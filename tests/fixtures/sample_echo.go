package main

import "github.com/labstack/echo/v4"

func main() {
	e := echo.New()
	e.GET("/users", getUsers)
	e.POST("/users", createUser)
}

func getUsers(c echo.Context) error  { return nil }
func createUser(c echo.Context) error { return nil }
