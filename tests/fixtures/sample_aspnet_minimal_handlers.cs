var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

static string Health() => "ok";

static class Handlers
{
    public static string Ping()
    {
        return "pong";
    }
}

app.MapGet("/health", Health);
app.MapMethods("/ping", new [] { "GET", "POST" }, Handlers.Ping);