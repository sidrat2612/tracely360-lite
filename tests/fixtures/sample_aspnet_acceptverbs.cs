using Microsoft.AspNetCore.Mvc;

[Route("api/items")]
public class ItemsController : ControllerBase
{
    [AcceptVerbs("GET", "POST", Route = "bulk")]
    public IActionResult Bulk()
    {
        return Ok();
    }
}