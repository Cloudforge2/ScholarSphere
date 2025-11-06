package com.example.Scholarsphere.controller;

import java.nio.charset.StandardCharsets;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.client.RestTemplate;

import com.example.Scholarsphere.model.Professor;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;


@Controller
public class MainController {

    private final RestTemplate restTemplate = new RestTemplate();
    private static final String FETCH_AUTHORS_BY_NAME_URL = "http://scrappy:8083/api/fetch-authors-by-name?name=";


    @GetMapping("/main")
    public String mainPage() {
        return "main"; // main.html template
    }

//     @GetMapping("/search")
// public String searchProfessors(@RequestParam(required = false) String professor,
//                                Model model) {
//     if (professor != null && !professor.isEmpty()) {
//         // Redirect to graph page; ProfessorGraphController will fetch the graph
//         return "redirect:/professor-graph?name=" + URLEncoder.encode(professor, StandardCharsets.UTF_8);
//     }

//     // If no name entered, render main page as before
//     return "main";
// }



    @GetMapping("/search")
    public String searchProfessors(@RequestParam(required = false) String professor, Model model) {
        if (professor != null && !professor.isEmpty()) {
            try {
                System.out.println("Searching for professor: " + professor);
                // Call your local service to fetch authors
                String url = FETCH_AUTHORS_BY_NAME_URL + URLEncoder.encode(professor, StandardCharsets.UTF_8);
                Professor[] professors = restTemplate.getForObject(url, Professor[].class);

                if (professors == null || professors.length == 0) {
                    model.addAttribute("error", "No authors found for name: " + professor);
                    return "main";
                }

                System.out.println("Returned professor: " + new ObjectMapper().writeValueAsString(professors[0]));


                // Multiple authors found → show selection page
                model.addAttribute("authors", professors);
                model.addAttribute("searchName", professor);
                return "author-selection";

            } catch (Exception e) {
                e.printStackTrace();
                model.addAttribute("error", "Error fetching authors: " + e.getMessage());
                return "main";
            }
        }

        // No professor name entered → go back to main search
        return "main";
    }
}



