package com.example.Scholarsphere.controller;

import com.example.Scholarsphere.model.Paper;
import com.example.Scholarsphere.model.Professor;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.client.RestTemplate;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.*;
import java.util.Map;

@Controller
public class ProfessorGraphController {

    private final RestTemplate restTemplate;

    // Updated gateway service base URL for "by-name" endpoint
    private static final String GATEWAY_URL = "http://gateway-service:8081/api/professors/by-name?name=" ;
    private static final String PROFESSOR_BY_NAME_URL = "http://gateway-service:8081/api/professors/summary/by-name?name=";
    private static final String PAPER_BY_TITLE_URL = "http://gateway-service:8081/api/paper/by-title?title=";

    public ProfessorGraphController() {
        this.restTemplate = new RestTemplate();
    }

    // Endpoint to fetch professor graph by name
    @GetMapping("/professor-graph")
    public String professorGraphPage(@RequestParam String name, Model model) {
        try {
            // Encode name to handle spaces and special characters
            String url = GATEWAY_URL + URLEncoder.encode(name, StandardCharsets.UTF_8);

            // Fetch list of professors from gateway service
            Professor[] professors = restTemplate.getForObject(url, Professor[].class);

            if (professors == null || professors.length == 0) {
                throw new RuntimeException("No professor found for name: " + name);
            }

            // Take the first professor from the list (or implement selection logic)
            Professor prof = professors[0];

            // Prepare Cytoscape JSON
            List<Map<String, Object>> nodes = new ArrayList<>();
            List<Map<String, Object>> edges = new ArrayList<>();

            // Add professor node
            nodes.add(Map.of("data", Map.of(
                    "id", prof.getId(),
                    "label", prof.getDisplayName(),
                    "type", "prof"
            )));

            // Add paper nodes and edges if papers exist
            if (prof.getPapers() != null) {
                for (Paper paper : prof.getPapers()) {
                    nodes.add(Map.of("data", Map.of(
                            "id", paper.getId(),
                            "label", paper.getTitle(),
                            "type", "paper"
                    )));
                    edges.add(Map.of("data", Map.of(
                            "id", prof.getId() + "-" + paper.getId(),
                            "source", prof.getId(),
                            "target", paper.getId()
                    )));
                }
            }

            // Final graph JSON
            Map<String, Object> graphData = Map.of(
                    "nodes", nodes,
                    "edges", edges
            );

            ObjectMapper mapper = new ObjectMapper();
            String graphJson = mapper.writeValueAsString(graphData);

            model.addAttribute("graphJson", graphJson);
            model.addAttribute("paperCount", prof.getPapers() != null ? prof.getPapers().size() : 0);


        } catch (Exception e) {
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            System.err.println("Failed to fetch graph from gateway: " + e.getMessage());
        }

        return "professor-graph";
    }

   @GetMapping("/professor-summary")
public String professorSummary(@RequestParam String name, Model model) {
    try {
        String url = PROFESSOR_BY_NAME_URL + URLEncoder.encode(name, StandardCharsets.UTF_8);
        System.out.println("DEBUG: Calling summary service URL: " + url);

        // Fetch JSON as a single Map
        Map<String, Object> profMap = restTemplate.getForObject(url, Map.class);

        System.out.println("DEBUG: Raw response from summary service: " + profMap);

        if (profMap == null || profMap.isEmpty()) {
            throw new RuntimeException("No professor found for name: " + name);
        }

        // Map JSON to Professor object
        Professor prof = new Professor();
        prof.setId((String) profMap.getOrDefault("id", "")); // use empty string if id missing
        prof.setDisplayName((String) profMap.getOrDefault("author", "")); // 'author' matches JSON key
        System.out.println("DEBUG: Professor ID: " + prof.getId() + ", Name: " + prof.getDisplayName());

        // Map papers
        List<Map<String, Object>> paperMaps = (List<Map<String, Object>>) profMap.get("papers");
        if (paperMaps != null) {
            List<Paper> papers = paperMaps.stream().map(pm -> {
                Paper p = new Paper();
                p.setId(pm.getOrDefault("id", "").toString());
                p.setTitle((String) pm.get("title"));
                p.setVenue((String) pm.get("venue"));
                p.setYear(pm.get("year") instanceof Number ? ((Number) pm.get("year")).intValue() : 0);
                p.setAbstractText((String) pm.get("abstract"));
                return p;
            }).toList();
            prof.setPapers(papers);
        } else {
            prof.setPapers(Collections.emptyList());
        }

        System.out.println("DEBUG: Total papers fetched: " + prof.getPapers().size());

        model.addAttribute("professor", prof);

    } catch (Exception e) {
        System.err.println("ERROR: Could not fetch data for " + name + ": " + e.getMessage());
        e.printStackTrace();

        model.addAttribute("error", "Could not fetch data for " + name + ": " + e.getMessage());
        model.addAttribute("professor", new Professor()); // avoid null in Thymeleaf
    }

    return "professor-summary";
}



    /** ---------------------- PAPER SUMMARY ---------------------- */
    @GetMapping("/paper-summary")
    public String paperSummary(@RequestParam String title, Model model) {
        try {
            String url = PAPER_BY_TITLE_URL + URLEncoder.encode(title, StandardCharsets.UTF_8);
            Paper[] papers = restTemplate.getForObject(url, Paper[].class);

            if (papers == null || papers.length == 0) {
                throw new RuntimeException("No paper found for title: " + title);
            }

            Paper paper = papers[0];
            model.addAttribute("title", paper.getTitle());
            model.addAttribute("summary", "Paper '" + paper.getTitle() + "' has " +
                    (paper.getAuthors() != null ? paper.getAuthors().size() : 0) + " authors.");

        } catch (Exception e) {
            model.addAttribute("title", title);
            model.addAttribute("summary", "Could not fetch data for " + title + ": " + e.getMessage());
        }

        return "paper-summary";
    }
}
