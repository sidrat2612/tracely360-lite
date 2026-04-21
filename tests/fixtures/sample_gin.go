package main

import "github.com/gin-gonic/gin"

func main() {
	r := gin.Default()
	r.GET("/users", getUsers)
	r.POST("/users", createUser)
	r.DELETE("/users/:id", deleteUser)

	api := r.Group("/api")
	api.GET("/items", listItems)
	api.POST("/items", createItem)
}

func getUsers(c *gin.Context)   {}
func createUser(c *gin.Context) {}
func deleteUser(c *gin.Context) {}
func listItems(c *gin.Context)  {}
func createItem(c *gin.Context) {}
