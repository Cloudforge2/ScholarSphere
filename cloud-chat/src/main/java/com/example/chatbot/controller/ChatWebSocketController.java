package com.example.chatbot.controller;

import com.example.chatbot.model.Message;
import com.example.chatbot.model.User;
import com.example.chatbot.service.MessageService;
import com.example.chatbot.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.web.socket.messaging.SessionDisconnectEvent;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;

import java.security.Principal;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Controller
public class ChatWebSocketController {

    private final List<User> userList = new CopyOnWriteArrayList<>();
    private final Map<String, String> sessionUsernameMap = new ConcurrentHashMap<>(); // sessionId -> username

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @Autowired
    private MessageService messageService;

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



    @EventListener
    public void handleWebSocketDisconnectListener(SessionDisconnectEvent event) {
        StompHeaderAccessor headerAccessor = StompHeaderAccessor.wrap(event.getMessage());
        String sessionId = headerAccessor.getSessionId();
        String username = sessionUsernameMap.remove(sessionId);

        System.out.println("[DEBUG] Disconnect event for sessionId: " + sessionId + ", username: " + username);

        if (username != null) {
            List<User> allUsers = userService.getAllUsers();
            messagingTemplate.convertAndSend("/topic/users", allUsers);
            System.out.println("[DEBUG] Broadcast updated user list after disconnect");
        }
    }

    @MessageMapping("/chat.send")
    public void sendMessage(@Payload Message message, Principal principal) {
        if (message == null || message.getReceiver() == null || message.getReceiver().getUsername() == null) {
            System.out.println("[DEBUG] Invalid message received");
            return;
        }

        User sender = userService.findByUsername(principal.getName());
        User receiver = userService.findByUsername(message.getReceiver().getUsername());

        message.setSender(sender);
        message.setReceiver(receiver);

        Message saved = messageService.saveMessage(message);
        System.out.println("[DEBUG] Saved message from " + sender.getUsername() + " to " + receiver.getUsername());

        messagingTemplate.convertAndSendToUser(receiver.getUsername(), "/queue/messages", saved);
        messagingTemplate.convertAndSendToUser(sender.getUsername(), "/queue/messages", saved);
        System.out.println("[DEBUG] Sent message to both sender and receiver queues");
    }
}
