using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/users")]
public class UsersController : ControllerBase
{
    [HttpGet("")]
    public IActionResult ListUsers()
    {
        return Ok();
    }

    [HttpPost("create")]
    public IActionResult CreateUser()
    {
        return Ok();
    }
}

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/health", () => "ok");