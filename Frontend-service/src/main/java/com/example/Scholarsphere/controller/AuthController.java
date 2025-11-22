package com.example.Scholarsphere.controller;

import com.example.Scholarsphere.model.User;
import com.example.Scholarsphere.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.security.Principal;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;

@Controller
public class AuthController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    // Token storage (token → email)
    private final Map<String, String> resetTokenStore = new ConcurrentHashMap<>();
    private final Map<String, Long> tokenExpiryStore = new ConcurrentHashMap<>();

    // Temporary store for security-question stage (email -> boolean)
    private final Map<String, Boolean> securityVerifiedStore = new ConcurrentHashMap<>();

    // IISc email validation
    private static final Pattern IISC_EMAIL_PATTERN =
            Pattern.compile("^[A-Za-z0-9._%+-]+@iisc\\.ac\\.in$");

    // ---------------- HOME / LOGIN / REGISTER ----------------

    @GetMapping("/")
    public String index() {
        return "index";
    }

    @GetMapping("/register")
    public String registerPage() {
        return "register";
    }

    @GetMapping("/login")
    public String loginPage(@RequestParam(value = "error", required = false) String error,
                            @RequestParam(value = "logout", required = false) String logout,
                            Model model) {

        if (error != null) model.addAttribute("error", "Invalid username or password");
        if (logout != null) model.addAttribute("message", "You have been logged out successfully");

        return "login";
    }

    // REGISTER USER
    @PostMapping("/register")
    public String register(@RequestParam String username,
                           @RequestParam String password,
                           @RequestParam String securityQuestion,
                           @RequestParam String securityAnswer,
                           RedirectAttributes redirectAttributes) {

        if (!IISC_EMAIL_PATTERN.matcher(username).matches()) {
            redirectAttributes.addFlashAttribute("error",
                    "Registration allowed only with a valid IISc email.");
            return "redirect:/register";
        }

        if (userRepository.findByUsername(username) != null) {
            redirectAttributes.addFlashAttribute("error", "Username already taken.");
            return "redirect:/register";
        }

        User user = new User();
        user.setUsername(username);
        user.setPassword(passwordEncoder.encode(password));
        user.setSecurityQuestion(securityQuestion);
        user.setSecurityAnswer(securityAnswer.trim().toLowerCase());

        userRepository.save(user);

        redirectAttributes.addFlashAttribute("message", "Successfully registered! Please login.");
        return "redirect:/login";
    }

    // ---------------- LOGOUT ----------------

    @GetMapping("/logout-confirm")
    public String logoutConfirm() { return "logout"; }

    @GetMapping("/logout-success")
    public String logoutSuccess(RedirectAttributes redirectAttributes) {
        redirectAttributes.addFlashAttribute("message", "You have been logged out successfully");
        return "redirect:/login?logout";
    }

    // ---------------- CHANGE PASSWORD ----------------

    @GetMapping("/change-password")
    public String changePasswordPage() { return "change-password"; }

    @PostMapping("/change-password")
    public String changePassword(@RequestParam String currentPassword,
                                 @RequestParam String newPassword,
                                 Principal principal,
                                 RedirectAttributes redirectAttributes) {

        User user = userRepository.findByUsername(principal.getName());

        if (user == null) {
            redirectAttributes.addFlashAttribute("error", "User not found.");
            return "redirect:/change-password";
        }

        if (!passwordEncoder.matches(currentPassword, user.getPassword())) {
            redirectAttributes.addFlashAttribute("error", "Current password is incorrect.");
            return "redirect:/change-password";
        }

        user.setPassword(passwordEncoder.encode(newPassword));
        userRepository.save(user);

        redirectAttributes.addFlashAttribute("message", "Password updated successfully!");
        return "redirect:/main";
    }

    // ---------------- FORGOT PASSWORD (STEP 1 — Enter Email) ----------------

    @GetMapping("/forgot-password")
    public String forgotPasswordPage() {
        return "forgot-password";
    }

    @PostMapping("/forgot-password")
    public String verifyEmail(@RequestParam String email,
                              RedirectAttributes redirectAttributes,
                              Model model) {

        User user = userRepository.findByUsername(email);

        if (user == null) {
            redirectAttributes.addFlashAttribute("error", "No account found with this email.");
            return "redirect:/forgot-password";
        }

        // Show security question page
        model.addAttribute("email", email);
        model.addAttribute("securityQuestion", user.getSecurityQuestion());

        return "forgot-password-question";
    }

    // ---------------- FORGOT PASSWORD (STEP 2 — Verify Security Answer) ----------------

    @PostMapping("/forgot-password-question")
    public String checkSecurityAnswer(@RequestParam String email,
                                      @RequestParam String answer,
                                      RedirectAttributes redirectAttributes) {

        User user = userRepository.findByUsername(email);

        if (user == null) {
            redirectAttributes.addFlashAttribute("error", "User not found.");
            return "redirect:/forgot-password";
        }

        if (!user.getSecurityAnswer().equals(answer.trim().toLowerCase())) {
            redirectAttributes.addFlashAttribute("error", "Incorrect answer to the security question.");
            redirectAttributes.addFlashAttribute("email", email);
            return "redirect:/forgot-password";
        }

        // Mark verified
        securityVerifiedStore.put(email, true);

        // Create secure reset token
        String token = UUID.randomUUID().toString();
        resetTokenStore.put(token, email);
        tokenExpiryStore.put(token, System.currentTimeMillis() + 10 * 60 * 1000);

        return "redirect:/reset-password?token=" + token;
    }

    // ---------------- RESET PASSWORD (FINAL STEP) ----------------

    @GetMapping("/reset-password")
    public String resetPasswordPage(@RequestParam String token,
                                    RedirectAttributes redirectAttributes,
                                    Model model) {

        if (!resetTokenStore.containsKey(token)) {
            redirectAttributes.addFlashAttribute("error", "Invalid or expired reset link.");
            return "redirect:/forgot-password";
        }

        if (System.currentTimeMillis() > tokenExpiryStore.get(token)) {
            resetTokenStore.remove(token);
            tokenExpiryStore.remove(token);
            redirectAttributes.addFlashAttribute("error", "Reset link expired.");
            return "redirect:/forgot-password";
        }

        model.addAttribute("token", token);
        return "reset-password";
    }

    @PostMapping("/reset-password")
    public String resetPassword(@RequestParam String token,
                                @RequestParam String newPassword,
                                RedirectAttributes redirectAttributes) {

        if (!resetTokenStore.containsKey(token)) {
            redirectAttributes.addFlashAttribute("error", "Invalid reset link.");
            return "redirect:/forgot-password";
        }

        String email = resetTokenStore.get(token);
        User user = userRepository.findByUsername(email);

        if (user == null) {
            redirectAttributes.addFlashAttribute("error", "User not found.");
            return "redirect:/forgot-password";
        }

        user.setPassword(passwordEncoder.encode(newPassword));
        userRepository.save(user);

        resetTokenStore.remove(token);
        tokenExpiryStore.remove(token);
        securityVerifiedStore.remove(email);

        redirectAttributes.addFlashAttribute("message", "Password reset successfully! Login again.");
        return "redirect:/login";
    }
}
