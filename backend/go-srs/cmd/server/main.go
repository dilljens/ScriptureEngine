// ScriptureEngine Memorization Server
//
// Go microservice providing FSRS-5 spaced repetition, memory palaces,
// verse sync, and review queue management.
//
// Usage:
//   go run cmd/server/main.go
//   ./go-srs  [--db /path/to/memorize.db] [--port 8090]

package main

import (
	"context"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/dillon/scriptureengine/go-srs/internal/db"
	"github.com/dillon/scriptureengine/go-srs/internal/handlers"
)

func main() {
	port := flag.String("port", "8090", "HTTP port")
	dbPath := flag.String("db", "data/memorize.db", "SQLite database path")
	flag.Parse()

	// Open database
	database, err := db.Open(*dbPath)
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}
	defer database.Close()
	log.Printf("Connected to database: %s", *dbPath)

	// Create handler and register routes
	h := handlers.New(database)
	mux := http.NewServeMux()
	h.RegisterRoutes(mux)

	// Apply middleware
	var srv http.Handler = mux
	srv = handlers.LoggingMiddleware(srv)
	srv = handlers.CORSMiddleware(srv)

	// Create HTTP server
	server := &http.Server{
		Addr:         ":" + *port,
		Handler:      srv,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in a goroutine
	go func() {
		log.Printf("Memorization server starting on :%s", *port)
		log.Printf("Endpoints:")
		log.Printf("  GET  /health")
		log.Printf("  POST /api/memorize/verses/batch")
		log.Printf("  POST /api/memorize/cards")
		log.Printf("  GET  /api/memorize/queue")
		log.Printf("  POST /api/memorize/review/:id")
		log.Printf("  GET  /api/memorize/verses/:ref/cards")
		log.Printf("  GET  /api/memorize/stats")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server error: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server stopped")
}
