package com.example.chatbot.controller;

import com.example.chatbot.model.Message;
import com.example.chatbot.model.User;
import com.example.chatbot.service.MessageService;
import com.example.chatbot.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.List;

@Controller
@RequestMapping("/chat")
public class ChatController {

    @Autowired
    private MessageService chatService;

    @Autowired
    private UserService userService;
@GetMapping
public String chatPage(@RequestParam(value = "user", required = false) String username,
                       Model model, Principal principal) {

    String currentUsername = principal.getName();
    User currentUser = userService.findByUsername(currentUsername); // ✅ get User object

    // Load all other users
    List<User> users = userService.getAllUsersExcept(currentUsername);
    model.addAttribute("users", users);

    // Determine selected user
    User selectedUser = null;
    if (username != null) {
        selectedUser = userService.findByUsername(username); // ✅ returns User
    }
    if (selectedUser == null && !users.isEmpty()) {
        selectedUser = users.get(0);
    }
    model.addAttribute("selectedUser", selectedUser);

    // Load messages between logged-in user and selected user
    List<Message> messages;
    if (selectedUser != null) {
        messages = chatService.getConversation(currentUser, selectedUser); // ✅ pass User objects
    } else {
        messages = List.of();
    }
    model.addAttribute("messages", messages);

    // Add empty Message object for form
    model.addAttribute("newMessage", new Message());

    return "chat";
}

@PostMapping("/send")
public String sendMessage(@ModelAttribute("newMessage") Message message,
                          @RequestParam("receiver") String receiverUsername,
                          Principal principal) {

    User sender = userService.findByUsername(principal.getName());
    User receiver = userService.findByUsername(receiverUsername);

    message.setSender(sender);
    message.setReceiver(receiver);
    chatService.saveMessage(message);

    return "redirect:/chat?user=" + receiverUsername;
}


}
