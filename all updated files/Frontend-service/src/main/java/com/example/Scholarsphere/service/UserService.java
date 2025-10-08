package com.example.Scholarsphere.service;

import com.example.Scholarsphere.model.User;
import com.example.Scholarsphere.repository.UserRepository;

import org.springframework.stereotype.Service;
import org.springframework.security.crypto.password.PasswordEncoder;
import java.util.List;




@Service
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    public boolean register(String username, String password) {
        if (userRepository.findByUsername(username) != null) {
            return false; // user already exists
        }
        User user = new User();
        user.setUsername(username);
        user.setPassword(passwordEncoder.encode(password));
        userRepository.save(user);
        return true;
    }

    public User findByUsername(String username) {
        return userRepository.findByUsername(username);
    }

    public List<User> getAllUsers() {
    List<User> users = userRepository.findAll(); // fetch users from DB
    System.out.println("Users in DB: " + users);  // debug output
    return users;
}

    public List<User> getAllUsersExcept(String username) {
    return userRepository.findByUsernameNot(username);
}



}


