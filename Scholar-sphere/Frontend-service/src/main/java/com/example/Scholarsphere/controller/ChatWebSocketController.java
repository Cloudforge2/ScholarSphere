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

    
    private final Map<String, String> sessionUsernameMap = new ConcurrentHashMap<>(); // sessionId -> username

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    

    @Autowired
    private UserService userService;

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

    // Get all users
    List<User> allUsers = userService.getAllUsers();

    // Send each user a list of all others (excluding themselves)
    for (User u : allUsers) {
        List<User> others = allUsers.stream()
                                     .filter(user -> !user.getUsername().equals(u.getUsername()))
                                     .toList();
        messagingTemplate.convertAndSendToUser(u.getUsername(), "/queue/users", others);
    }
}



    
}
