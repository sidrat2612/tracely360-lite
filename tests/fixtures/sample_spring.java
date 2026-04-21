import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api")
public class UserController {

    @GetMapping("/users")
    public List<String> getUsers() {
        return List.of();
    }

    @PostMapping("/users")
    public String createUser() {
        return "created";
    }

    @DeleteMapping("/users/{id}")
    public void deleteUser(@PathVariable String id) {
    }

    @RequestMapping(value = "/ping", method = RequestMethod.GET)
    public String ping() {
        return "pong";
    }
}
