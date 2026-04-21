var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/health", Health);
app.MapMethods("/ping", new[] { "GET", "POST" }, Handlers.Ping);
