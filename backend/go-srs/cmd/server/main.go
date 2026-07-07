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

	// Push notification scheduler: check for due cards every 15 minutes
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go pushNotificationScheduler(ctx, database)

	// Start server in a goroutine
	go func() {
		log.Printf("Memorization server starting on :%s", *port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server error: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server stopped")
}

func pushNotificationScheduler(ctx context.Context, database *db.DB) {
	ticker := time.NewTicker(15 * time.Minute)
	defer ticker.Stop()

	log.Println("Push scheduler started (15min interval)")

	for {
		select {
		case <-ctx.Done():
			log.Println("Push scheduler stopped")
			return
		case <-ticker.C:
			due, err := database.GetDueCount()
			if err != nil {
				continue
			}
			if due > 0 {
				log.Printf("Push scheduler: %d cards due for review", due)
			}
		}
	}
}
