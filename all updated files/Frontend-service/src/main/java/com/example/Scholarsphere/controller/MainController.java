package com.example.Scholarsphere.controller;

import java.nio.charset.StandardCharsets;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;


@Controller
public class MainController {

    @GetMapping("/main")
    public String mainPage() {
        return "main"; // main.html template
    }

    @GetMapping("/search")
public String searchProfessors(@RequestParam(required = false) String professor,
                               Model model) {
    if (professor != null && !professor.isEmpty()) {
        // Redirect to graph page; ProfessorGraphController will fetch the graph
        return "redirect:/professor-graph?name=" + URLEncoder.encode(professor, StandardCharsets.UTF_8);
    }

    // If no name entered, render main page as before
    return "main";
}

}
