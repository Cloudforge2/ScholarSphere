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
import java.util.*;

@Controller
public class ProfessorGraphController {

    private final RestTemplate restTemplate;

    // Updated gateway service base URL for "by-name" endpoint
    private static final String GATEWAY_URL = "http://gateway-service:8081/api/professors/by-name?name=" ;
    private static final String PROFESSOR_BY_NAME_URL = "http://gateway-service:8081/api/professors/summary/by-name?name=";
    private static final String PAPER_BY_TITLE_URL = "http://gateway-service:8081/api/paper/by-title?title=";
    private static final String FETCH_AUTHOR_BY_ID_URL = "http://scrappy:8083/api/fetch-author-by-id?id=";
    private static final String GRAPH_SERVICE_URL = "http://graph-service:8082/api/professors/";

    public ProfessorGraphController() {
        this.restTemplate = new RestTemplate();
    }

    // Endpoint to fetch professor graph by name
    @GetMapping("/professor-graph")
    public String professorGraphPage(@RequestParam String id, Model model) {
        try {
            String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);

            // Step 1️⃣ Check if author data already exists in Neo4j
            String existsUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
            Boolean exists = restTemplate.getForObject(existsUrl, Boolean.class);

            if (exists == null || !exists) {
                System.out.println("🟠 Author not found in Neo4j, triggering Scrappy...");
                String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
                restTemplate.getForObject(fetchUrl, String.class);  // trigger Scrappy ingestion

                // Optional: short delay or polling loop (Scrappy may take ~2–4 sec)
                Thread.sleep(3000);
            } else {
                System.out.println("✅ Author already present in Neo4j. Skipping Scrappy ingestion.");
            }

            // Step 2️⃣ Fetch graph data
            String graphUrl = GRAPH_SERVICE_URL + encodedId + "/graph";
            Professor prof = restTemplate.getForObject(graphUrl, Professor.class);
            System.out.println("Graph-service returned: " + prof);

            if (prof == null) {
                throw new RuntimeException("Graph service returned null professor for ID: " + id);
            }
            

            

            // 3️⃣ Build Cytoscape data (with coauthors)
            List<Map<String, Object>> nodes = new ArrayList<>();
            List<Map<String, Object>> edges = new ArrayList<>();

            Set<String> addedNodeIds = new HashSet<>(); // To avoid duplicates

            // --- Add main professor node ---
            nodes.add(Map.of("data", Map.of(
                    "id", prof.getId(),
                    "label", prof.getDisplayName(),
                    "type", "prof"
            )));
            addedNodeIds.add(prof.getId());

            // --- Add papers and coauthors ---
            if (prof.getPapers() != null) {
                for (Paper paper : prof.getPapers()) {

                    // Add paper node
                    if (!addedNodeIds.contains(paper.getId())) {
                        nodes.add(Map.of("data", Map.of(
                                "id", paper.getId(),
                                "label", paper.getTitle(),
                                "type", "paper"
                        )));
                        addedNodeIds.add(paper.getId());
                    }

                    // Add edge: main professor -> paper
                    edges.add(Map.of("data", Map.of(
                            "id", prof.getId() + "-" + paper.getId(),
                            "source", prof.getId(),
                            "target", paper.getId()
                    )));

                    // Add coauthor nodes and edges (if available)
                    if (paper.getAuthors() != null) {
                        for (Professor coauthor : paper.getAuthors()) {
                            // Skip main author (already added)
                            if (coauthor.getId().equals(prof.getId())) continue;

                            // Add coauthor node (if not already added)
                            if (!addedNodeIds.contains(coauthor.getId())) {
                                nodes.add(Map.of("data", Map.of(
                                        "id", coauthor.getId(),
                                        "label", coauthor.getDisplayName(),
                                        "type", "coauthor"
                                )));
                                addedNodeIds.add(coauthor.getId());
                            }

                            // Add edge: coauthor -> paper
                            edges.add(Map.of("data", Map.of(
                                    "id", coauthor.getId() + "-" + paper.getId(),
                                    "source", coauthor.getId(),
                                    "target", paper.getId()
                            )));
                        }
                    }
                }
            }

            // --- Build graph JSON ---
            ObjectMapper mapper = new ObjectMapper();
            String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

            // --- Add to model ---
            model.addAttribute("graphJson", graphJson);
            model.addAttribute("professorName", prof.getDisplayName());
            model.addAttribute("paperCount", prof.getPapers() != null ? prof.getPapers().size() : 0);
        

        return "professor-graph";
    }
        catch (Exception e) {
            System.err.println("ERROR: Could not fetch graph for professor ID " + id + ": " + e.getMessage());
            e.printStackTrace();

            model.addAttribute("error", "Could not fetch graph for professor ID " + id + ": " + e.getMessage());
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", "Unknown");
            model.addAttribute("paperCount", 0);

            return "professor-graph";
        }
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
            String url = PAPER_BY_TITLE_URL + title;
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
