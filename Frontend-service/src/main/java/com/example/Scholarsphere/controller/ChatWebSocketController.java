package com.example.Scholarsphere.controller;

import com.example.Scholarsphere.model.User;
import com.example.Scholarsphere.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;

import java.security.Principal;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Controller
public class ChatWebSocketController {

    private final Map<String, String> sessionUsernameMap = new ConcurrentHashMap<>();

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @Autowired
    private UserService userService;

    // WebSocket login
    @MessageMapping("/login")
    public void login(StompHeaderAccessor accessor, Principal principal) {
        if (principal == null) {
            System.out.println("[DEBUG] Login called without authenticated principal!");
            return;
        }

        String username = principal.getName();
        String sessionId = accessor.getSessionId();
        System.out.println("[DEBUG] Login called for: " + username + ", sessionId: " + sessionId);

        sessionUsernameMap.put(sessionId, username);

        // Fetch all users
        List<User> allUsers = userService.getAllUsers();

        // Send each user every other user
        for (User u : allUsers) {
            List<User> others = allUsers.stream()
                    .filter(user -> !user.getUsername().equals(u.getUsername()))
                    .toList();

            messagingTemplate.convertAndSendToUser(u.getUsername(), "/queue/users", others);
        }
    }

    // --------------- NEW LOGOUT HANDLER --------------------

    @MessageMapping("/logout")
    public void websocketLogout(StompHeaderAccessor accessor, Principal principal) {
        if (principal == null) {
            System.out.println("[DEBUG] Logout called without principal!");
            return;
        }

        String sessionId = accessor.getSessionId();
        String username = sessionUsernameMap.get(sessionId);

        if (username != null) {
            System.out.println("[DEBUG] Logging out WebSocket user: " + username);

            // Remove session mapping
            sessionUsernameMap.remove(sessionId);

            // Notify frontend that logout was successful
            messagingTemplate.convertAndSendToUser(username, "/queue/logout", "LOGOUT_SUCCESS");
        }
    }
}
