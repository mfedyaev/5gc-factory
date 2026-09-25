package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

const (
	ValidUdm  = "UDM"
	ValidAmf  = "AMF"
	ValidAusf = "AUSF"
	ValidUdr  = "UDR"
)

var nfTypes = map[string]bool{
	ValidUdm:  true,
	ValidAmf:  true,
	ValidAusf: true,
	ValidUdr:  true,
}

const (
	StatusRegistered = "REGISTERED"
	StatusSuspended  = "SUSPENDED"
)

var nfStatuses = map[string]bool{
	StatusRegistered: true,
	StatusSuspended:  true,
}

var fqdnRegex = regexp.MustCompile(`^([0-9A-Za-z]([-0-9A-Za-z]{0,61}[0-9A-Za-z])?\.)+[A-Za-z]{2,63}\.?$`)

type NFProfile struct {
	NfInstanceId string `json:"nfInstanceId"`
	NfType       string `json:"nfType"`
	NfStatus     string `json:"nfStatus"`
	Fqdn         string `json:"fqdn"`
}

type SearchResult struct {
	ValidityPeriod int         `json:"validityPeriod"`
	NfInstances    []NFProfile `json:"nfInstances"`
}

type ProblemDetails struct {
	Title  string `json:"title,omitempty"`
	Status int    `json:"status,omitempty"`
	Detail string `json:"detail"`
}

func sendError(w http.ResponseWriter, status int, detail string) {
	w.Header().Set("Content-Type", "application/problem+json")
	w.WriteHeader(status)
	resp := ProblemDetails{
		Title:  http.StatusText(status),
		Status: status,
		Detail: detail,
	}
	json.NewEncoder(w).Encode(resp)
}

type Service struct {
	client         *mongo.Client
	db             *mongo.Database
	collection     *mongo.Collection
	validityPeriod int
}

func NewService() (*Service, error) {
	portStr := os.Getenv("PORT")
	if portStr == "" {
		portStr = "8080"
	}

	validityPeriodStr := os.Getenv("VALIDITY_PERIOD")
	validityPeriod := 3600
	if validityPeriodStr != "" {
		vp, err := strconv.Atoi(validityPeriodStr)
		if err == nil {
			validityPeriod = vp
		}
	}

	mongoURI := os.Getenv("MONGO_URI")
	if mongoURI == "" {
		mongoURI = "mongodb://localhost:27017"
	}

	client, err := mongo.Connect(context.Background(), options.Client().ApplyURI(mongoURI))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to MongoDB: %w", err)
	}

	if err := client.Ping(context.Background(), nil); err != nil {
		return nil, fmt.Errorf("failed to ping MongoDB: %w", err)
	}

	log.Println("Connected to MongoDB")

	db := client.Database("nrf")
	collection := db.Collection("nf_instances")

	return &Service{
		client:         client,
		db:             db,
		collection:     collection,
		validityPeriod: validityPeriod,
	}, nil
}

func (s *Service) HandleRegister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		sendError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	nfInstanceID := r.PathValue("nfInstanceID")
	if nfInstanceID == "" {
		sendError(w, http.StatusBadRequest, "nfInstanceID is required")
		return
	}

	var profile NFProfile
	if err := json.NewDecoder(r.Body).Decode(&profile); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	if profile.NfInstanceId != nfInstanceID {
		sendError(w, http.StatusBadRequest, "nfInstanceId in request body does not match nfInstanceId in URI path.")
		return
	}

	if !nfTypes[profile.NfType] {
		sendError(w, http.StatusBadRequest, "nfType is not one of the allowed enum values: UDM, AMF, AUSF, UDR.")
		return
	}

	if !nfStatuses[profile.NfStatus] {
		sendError(w, http.StatusBadRequest, "nfStatus is not one of the allowed enum values: REGISTERED, SUSPENDED.")
		return
	}

	if len(profile.Fqdn) < 4 {
		sendError(w, http.StatusBadRequest, "fqdn length is below the minimum of 4.")
		return
	}

	if len(profile.Fqdn) > 253 {
		sendError(w, http.StatusBadRequest, "fqdn length exceeds the maximum of 253.")
		return
	}

	if !fqdnRegex.MatchString(profile.Fqdn) {
		sendError(w, http.StatusBadRequest, "fqdn does not match the required format.")
		return
	}

	log.Printf("Processing RegisterNFInstance for NF Instance ID: %s", nfInstanceID)

	existing := s.collection.FindOne(context.Background(), bson.M{"nfInstanceId": nfInstanceID})
	if err := existing.Err(); err != nil {
		if err == mongo.ErrNoDocuments {
			doc := bson.M{
				"nfInstanceId": profile.NfInstanceId,
				"nfType":       profile.NfType,
				"nfStatus":     profile.NfStatus,
				"fqdn":         profile.Fqdn,
			}
			_, err := s.collection.InsertOne(context.Background(), doc)
			if err != nil {
				sendError(w, http.StatusInternalServerError, "Failed to insert NF Instance")
				return
			}
			log.Printf("Created new NF Instance: %s", nfInstanceID)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(profile)
		} else {
			sendError(w, http.StatusInternalServerError, "Database error")
		}
	} else {
		doc := bson.M{
			"$set": bson.M{
				"nfInstanceId": profile.NfInstanceId,
				"nfType":       profile.NfType,
				"nfStatus":     profile.NfStatus,
				"fqdn":         profile.Fqdn,
			},
		}
		_, err := s.collection.UpdateOne(context.Background(), bson.M{"nfInstanceId": nfInstanceID}, doc)
		if err != nil {
			sendError(w, http.StatusInternalServerError, "Failed to update NF Instance")
			return
		}
		log.Printf("Updated existing NF Instance: %s", nfInstanceID)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(profile)
	}
}

func (s *Service) HandleDeregister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		sendError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	nfInstanceID := r.PathValue("nfInstanceID")
	if nfInstanceID == "" {
		sendError(w, http.StatusBadRequest, "nfInstanceID is required")
		return
	}

	log.Printf("Processing NFDeregister for NF Instance ID: %s", nfInstanceID)

	result, err := s.collection.DeleteOne(context.Background(), bson.M{"nfInstanceId": nfInstanceID})
	if err != nil {
		sendError(w, http.StatusInternalServerError, "Database error")
		return
	}

	if result.DeletedCount == 0 {
		sendError(w, http.StatusNotFound, "NF Instance not found.")
		return
	}

	log.Printf("Deleted NF Instance: %s", nfInstanceID)
	w.WriteHeader(http.StatusNoContent)
}

func (s *Service) HandleDiscover(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		sendError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	targetNFType := r.URL.Query().Get("target-nf-type")
	requesterNFType := r.URL.Query().Get("requester-nf-type")

	if targetNFType == "" || !nfTypes[targetNFType] {
		sendError(w, http.StatusBadRequest, "target-nf-type is not one of the allowed enum values: UDM, AMF, AUSF, UDR.")
		return
	}

	if requesterNFType == "" || !nfTypes[requesterNFType] {
		sendError(w, http.StatusBadRequest, "requester-nf-type is not one of the allowed enum values: UDM, AMF, AUSF, UDR.")
		return
	}

	log.Printf("Processing NFDiscover for Target NF Type: %s, Requester NF Type: %s", targetNFType, requesterNFType)

	cursor, err := s.collection.Find(context.Background(), bson.M{
		"nfType":   targetNFType,
		"nfStatus": StatusRegistered,
	})
	if err != nil {
		sendError(w, http.StatusInternalServerError, "Database error")
		return
	}
	defer cursor.Close(context.Background())

	var profiles []NFProfile
	if err := cursor.All(context.Background(), &profiles); err != nil {
		sendError(w, http.StatusInternalServerError, "Database error")
		return
	}

	log.Printf("Discovery completed. Found %d instances.", len(profiles))

	result := SearchResult{
		ValidityPeriod: s.validityPeriod,
		NfInstances:    profiles,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(result)
}

func (s *Service) HandleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		sendError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}
	w.WriteHeader(http.StatusOK)
}

func main() {
	log.Println("Starting NRF Service...")

	svc, err := NewService()
	if err != nil {
		log.Fatalf("Failed to initialize service: %v", err)
	}

	mux := http.NewServeMux()

	mux.HandleFunc("PUT /nnrf-nfm/v1/nf-instances/{nfInstanceID}", svc.HandleRegister)
	mux.HandleFunc("DELETE /nnrf-nfm/v1/nf-instances/{nfInstanceID}", svc.HandleDeregister)
	mux.HandleFunc("GET /nnrf-disc/v1/nf-instances", svc.HandleDiscover)
	mux.HandleFunc("GET /health", svc.HandleHealth)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Listening on port %s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
