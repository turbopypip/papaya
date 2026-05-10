package http_server

import (
	"log"
	"net/http"
	"vkid-backend/internal/config"
	r "vkid-backend/internal/http-server/router"
)

func RunServer() {
	cfg := config.MustLoad()
	router := r.InitRouter()

	// Set up a server
	srv := &http.Server{
		Addr:         cfg.Address,
		Handler:      router, // gin router
		ReadTimeout:  cfg.Timeout,
		WriteTimeout: cfg.Timeout,
		IdleTimeout:  cfg.IdleTimeout,
	}

	// Start server
	log.Println("Starting server on", cfg.Address)
	err := srv.ListenAndServe()
	if err != nil {
		log.Fatal("ListenAndServe: ", err)
	}
}
