package com.example.chatbot.service;

import com.example.chatbot.model.Message;
import com.example.chatbot.model.User;
import com.example.chatbot.repository.MessageRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class MessageService {

    @Autowired
    private MessageRepository messageRepository;

    // Save new message
    public Message saveMessage(Message message) {
        return messageRepository.save(message);
    }

    // Get all messages
    public List<Message> getAllMessages() {
        return messageRepository.findAll();
    }

    // Get all messages sent by a user
    public List<Message> getMessagesBySender(User sender) {
        return messageRepository.findBySender(sender);
    }

    // Get all messages received by a user
    public List<Message> getMessagesByReceiver(User receiver) {
        return messageRepository.findByReceiver(receiver);
    }

    // Get conversation between two users
    public List<Message> getConversation(User sender, User receiver) {
        return messageRepository.findBySenderAndReceiver(sender, receiver);
    }
}

