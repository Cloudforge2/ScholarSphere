package com.example.Scholarsphere.controller;

import com.example.Scholarsphere.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.util.regex.Pattern;

@Controller
public class AuthController {

    @Autowired
    private UserService userService;

    // Regex pattern to match IISc email IDs
    private static final Pattern IISC_EMAIL_PATTERN = Pattern.compile("^[A-Za-z0-9._%+-]+@iisc\\.ac\\.in$");

    // Show index page at root
    @GetMapping("/")
    public String index() {
        return "index"; // thymeleaf template: src/main/resources/templates/index.html
    }

    // Show register page
    @GetMapping("/register")
    public String registerPage() {
        return "register"; // thymeleaf template register.html
    }

    // Show login page
    @GetMapping("/login")
    public String loginPage(@RequestParam(value = "error", required = false) String error,
                            @RequestParam(value = "logout", required = false) String logout,
                            Model model) {
        if (error != null) {
            model.addAttribute("error", "Invalid username or password");
        }
        if (logout != null) {
            model.addAttribute("message", "You have been logged out successfully");
        }
        return "login";
    }

    // Handle registration
    @PostMapping("/register")
    public String register(@RequestParam String username,
                           @RequestParam String password,
                           RedirectAttributes redirectAttributes) {

        // Validate IISc email
        if (!IISC_EMAIL_PATTERN.matcher(username).matches()) {
            redirectAttributes.addFlashAttribute("error", "Registration is allowed only with a valid IISc email ID.");
            return "redirect:/register";
        }

        // Attempt registration
        boolean success = userService.register(username, password);
        if (success) {
            redirectAttributes.addFlashAttribute("message", "Successfully registered! Please login.");
            return "redirect:/login";
        } else {
            redirectAttributes.addFlashAttribute("error", "Username already taken.");
            return "redirect:/register";
        }
    }
}
