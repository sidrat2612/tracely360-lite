package main

import (
	"net/http"

	"github.com/go-chi/chi/v5"
)

func main() {
	r := chi.NewRouter()
	r.Get("/users", listUsers)
	r.Post("/users", createUser)
	r.Delete("/users/{id}", deleteUser)
}

func listUsers(w http.ResponseWriter, r *http.Request)   {}
func createUser(w http.ResponseWriter, r *http.Request)  {}
func deleteUser(w http.ResponseWriter, r *http.Request)   {}
