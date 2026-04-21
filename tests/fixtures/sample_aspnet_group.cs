var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

var api = app.MapGroup("/api");
api.MapGet("/users", () => "ok");

app.MapMethods("/ping", new [] { "GET", "POST" }, () => "pong");