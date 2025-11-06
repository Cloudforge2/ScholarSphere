package com.example.Scholarsphere.controller;

import com.example.Scholarsphere.model.Paper;
import com.example.Scholarsphere.model.Professor;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.client.RestTemplate;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Controller
public class ProfessorGraphController {

    private final RestTemplate restTemplate;

    // Updated gateway service base URL for "by-name" endpoint

    private static final String PROFESSOR_BY_ID_URL = "http://summary-service:8085/professors/summary/by-id?id=";
    private static final String PAPER_BY_TITLE_URL = "http://summary-service:8085/papers/by-title?title=";
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

            
            // Step 1️⃣ Check if author should be ingested in Neo4j
            String shouldIngestUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
            Boolean shouldIngest = restTemplate.getForObject(shouldIngestUrl, Boolean.class);


            // if (exists == null || !exists) {
            //     System.out.println("🟠 Author not found in Neo4j, triggering Scrappy...");
            //     String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
            //     restTemplate.getForObject(fetchUrl, String.class);  // trigger Scrappy ingestion
            if (Boolean.TRUE.equals(shouldIngest)) {
                System.out.println("🟠 Author not found or not fully ingested, triggering Scrappy...");
                String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
                restTemplate.getForObject(fetchUrl, String.class);
    

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
public String professorSummary(@RequestParam String id, Model model) { // <-- CHANGED from "name" to "id"
    try {
        // Use the professor ID to build the request URL
        String url = PROFESSOR_BY_ID_URL + (id);
        System.out.println("DEBUG: Calling summary service URL: " + url);

        // Fetch the summary data using the ID
        // The response is expected to be a Map, which is fine
        Map<String, Object> profMap = restTemplate.getForObject(url, Map.class);
        System.out.println("DEBUG: Raw response from summary service: " + profMap);

        if (profMap == null || profMap.isEmpty()) {
            throw new RuntimeException("No professor summary found for ID: " + id);
        }

        // Map the response fields to the model attributes for Thymeleaf
        // Use a default value for author name if not present in the response
        model.addAttribute("author", profMap.getOrDefault("display_name", "Professor"));
        model.addAttribute("summary", profMap.getOrDefault("research_summary", "No summary available."));
        model.addAttribute("papers_analyzed_count", profMap.getOrDefault("papers_analyzed_count", "N/A"));
        model.addAttribute("papers_sample", profMap.getOrDefault("papers_sample", Collections.emptyList()));

    } catch (Exception e) {
        System.err.println("ERROR: Could not fetch summary for professor ID " + id + ": " + e.getMessage());
        e.printStackTrace();

        // Populate the model with error information for the user
        model.addAttribute("error", "Could not fetch summary for professor with ID: " + id);
        model.addAttribute("author", "Unknown Professor");
    }

    // Return the name of the Thymeleaf HTML template
    return "professor-summary";
}


    

    @GetMapping("/coauthor-graph")
    public String coauthorGraphPage(@RequestParam String id, Model model) {
        try {
            String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
            System.out.println("👥 Generating Coauthor Graph for: " + id);

            // Check existence
            String shouldIngestUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
            Boolean shouldIngest = restTemplate.getForObject(shouldIngestUrl, Boolean.class);


            // if (exists == null || !exists) {
            //     System.out.println("🟠 Author not found in Neo4j, triggering Scrappy...");
            //     String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
            //     restTemplate.getForObject(fetchUrl, String.class);  // trigger Scrappy ingestion
            if (Boolean.TRUE.equals(shouldIngest)) {
                System.out.println("🟠 Author not found or not fully ingested, triggering Scrappy...");
                String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
                restTemplate.getForObject(fetchUrl, String.class);
    
                Thread.sleep(3000);
            }
            // Step 2️⃣ Fetch graph data
            String graphUrl = GRAPH_SERVICE_URL + encodedId + "/graph";
            Professor prof = restTemplate.getForObject(graphUrl, Professor.class);
            System.out.println("Graph-service returned: " + prof);

            if (prof == null) {
                throw new RuntimeException("Graph service returned null professor for ID: " + id);
            }
            // Fetch coauthors
            String coauthorUrl = GRAPH_SERVICE_URL + "coauthors?id=" + encodedId;
            Professor[] coauthors = restTemplate.getForObject(coauthorUrl, Professor[].class);

            List<Map<String, Object>> nodes = new ArrayList<>();
            List<Map<String, Object>> edges = new ArrayList<>();
            Set<String> addedNodeIds = new HashSet<>();

            // Main professor node
            nodes.add(Map.of("data", Map.of(
                    "id", prof.getId(),
                    "label", prof.getDisplayName(),
                    "type", "prof"
            ))); 
            addedNodeIds.add(id);

            // Coauthor nodes + edges
            if (coauthors != null) {
                for (Professor co : coauthors) {
                    if (!addedNodeIds.contains(co.getId())) {
                        nodes.add(Map.of("data", Map.of(
                                "id", co.getId(),
                                "label", co.getDisplayName(),
                                "type", "coauthor"
                        )));
                        addedNodeIds.add(co.getId());
                    }

                    edges.add(Map.of("data", Map.of(
                            "id", id + "-" + co.getId(),
                            "source", id,
                            "target", co.getId()
                    )));
                }
            }

            ObjectMapper mapper = new ObjectMapper();
            String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

            model.addAttribute("graphJson", graphJson);
            model.addAttribute("professorName", "Coauthor Network");
            System.out.println("DEBUG: Coauthor graph JSON: " + graphJson);

            // 👉 return new view here
            return "professor-graph-coauthor";

        } catch (Exception e) {
            e.printStackTrace();
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", "Error");
            return "professor-graph-coauthor";
        }
    }

    
@GetMapping("/paper-summary")
    public String paperSummary(@RequestParam(required = false) String title,
                               @RequestParam(required = false) String id,
                               Model model) {
        String paperId = null;
        Paper paper = new Paper();
    
        try {
            // 1️⃣ Determine paper ID
            if (id != null && !id.isEmpty()) {
                paperId = id;
                System.out.println("✅ Using provided paper ID: " + paperId);
                paper.setId(paperId);
                paper.setTitle(title != null ? title : "Unknown Paper");
            } else if (title != null && !title.isEmpty()) {
                String url = PAPER_BY_TITLE_URL + URLEncoder.encode(title, StandardCharsets.UTF_8);
                System.out.println("DEBUG: Fetching paper metadata from: " + url);
                Paper[] papers = restTemplate.getForObject(url, Paper[].class);
    
                if (papers != null && papers.length > 0) {
                    paper = papers[0];
                    paperId = paper.getId();
                    System.out.println("DEBUG: Got paper ID from service: " + paperId);
                } else {
                    throw new RuntimeException("No paper found for title: " + title);
                }
            } else {
                throw new IllegalArgumentException("Either 'title' or 'id' parameter is required.");
            }
    
            // 2️⃣ Fetch paper summary from Summary Service (FastAPI)
            try {
                String summaryUrl;
    
                if (paperId != null) {
                    // ✅ Call /paper/by-id
                    summaryUrl = "http://summary-service:8085/paper/by-id?paper_id=" +
                            paperId;
                } else {
                    // ✅ Fallback: call /paper/by-title
                    summaryUrl = "http://summary-service:8085/paper/by-title?title=" +
                            URLEncoder.encode(title, StandardCharsets.UTF_8);
                }
    
                System.out.println("DEBUG: Fetching paper summary from: " + summaryUrl);
    
                Map<String, Object> summaryMap = restTemplate.getForObject(summaryUrl, Map.class);
                String summaryText;
    
                if (summaryMap != null && summaryMap.containsKey("summary")) {
                    summaryText = (String) summaryMap.getOrDefault("summary", "No summary available.");
                } else {
                    System.err.println("⚠️ No summary found in response for paper ID: " + paperId);
                    summaryText = "No summary available.";
                }
    
                model.addAttribute("summary", summaryText);
    
            } catch (Exception e) {
                System.err.println("⚠️ Could not fetch summary: " + e.getMessage());
                model.addAttribute("summary", "Summary unavailable — please try again later.");
            }
    
            // 3️⃣ Fetch authors from graph-service
            String authorsUrl = GRAPH_SERVICE_URL + "paper/authors?id=" +
                    URLEncoder.encode(paperId, StandardCharsets.UTF_8);
            System.out.println("DEBUG: Fetching authors from URL: " + authorsUrl);
    
            Professor[] authors = restTemplate.getForObject(authorsUrl, Professor[].class);
            System.out.println("DEBUG: Authors fetched: " + (authors != null ? authors.length : 0));
    
            // 4️⃣ Build Graph Data
            List<Map<String, Object>> nodes = new ArrayList<>();
            List<Map<String, Object>> edges = new ArrayList<>();
    
            // Paper node
            nodes.add(Map.of("data", Map.of(
                    "id", paperId,
                    "label", paper.getTitle(),
                    "type", "paper"
            )));
    
            // Author nodes
            if (authors != null) {
                for (Professor author : authors) {
                    nodes.add(Map.of("data", Map.of(
                            "id", author.getId(),
                            "label", author.getDisplayName(),
                            "type", "author"
                    )));
                    edges.add(Map.of("data", Map.of(
                            "id", paperId + "-" + author.getId(),
                            "source", paperId,
                            "target", author.getId()
                    )));
                }
            }
    
            // 5️⃣ Serialize and Add to Model
            ObjectMapper mapper = new ObjectMapper();
            String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));
    
            model.addAttribute("graphJson", graphJson);
            model.addAttribute("paper", paper);
            model.addAttribute("title", paper.getTitle());
            model.addAttribute("paperId", paperId);
    
        } catch (Exception e) {
            e.printStackTrace();
            model.addAttribute("title", title != null ? title : "Unknown Paper");
            model.addAttribute("summary", "Could not fetch data: " + e.getMessage());
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
        }
    
        return "paper-summary";
    }


    @GetMapping("/topic-graph")
public String topicGraphPage(@RequestParam String id, @RequestParam String name, Model model) {
    try {
        String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
        System.out.println("🌐 Generating Research Topic Graph for: " + id);

        // Step 1️⃣ Check if author exists
        String shouldIngestUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
            Boolean shouldIngest = restTemplate.getForObject(shouldIngestUrl, Boolean.class);


            // if (exists == null || !exists) {
            //     System.out.println("🟠 Author not found in Neo4j, triggering Scrappy...");
            //     String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
            //     restTemplate.getForObject(fetchUrl, String.class);  // trigger Scrappy ingestion
            if (Boolean.TRUE.equals(shouldIngest)) {
                System.out.println("🟠 Author not found or not fully ingested, triggering Scrappy...");
                String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
                restTemplate.getForObject(fetchUrl, String.class);
    
            Thread.sleep(3000);
        }

        // Step 2️⃣ Fetch topics of this author
        String topicUrl = GRAPH_SERVICE_URL + "topics?id=" + encodedId;
        String[] topics = restTemplate.getForObject(topicUrl, String[].class);

        if (topics == null || topics.length == 0) {
            System.out.println("⚠️ No topics found for author " + id);
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", "No Research Topics Found");
            return "professor-graph-topic";
        }

        // Step 3️⃣ Build graph nodes/edges
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Set<String> addedNodeIds = new HashSet<>();

        // Add author node
        nodes.add(Map.of("data", Map.of(
                "id", id,
                "label", name,
                "type", "prof"
        )));
        addedNodeIds.add(id);

        // Add topic nodes and edges
        for (String topic : topics) {
            String nodeId = topic.replaceAll("\\s+", "_");

            if (!addedNodeIds.contains(nodeId)) {
                nodes.add(Map.of("data", Map.of(
                        "id", nodeId,
                        "label", topic,
                        "type", "topic"
                )));
                addedNodeIds.add(nodeId);
            }

            edges.add(Map.of("data", Map.of(
                    "id", id + "-" + nodeId,
                    "source", id,
                    "target", nodeId
            )));
        }

        // Step 4️⃣ Convert to Cytoscape JSON
        ObjectMapper mapper = new ObjectMapper();
        String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

        model.addAttribute("graphJson", graphJson);
        model.addAttribute("professorName", name);
        System.out.println("✅ Topic graph JSON: " + graphJson);

        return "professor-graph-topic"; // ✅ Update HTML file accordingly

    } catch (Exception e) {
        e.printStackTrace();
        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
        model.addAttribute("professorName", "Error");
        return "professor-graph-topic";
    }
}


@GetMapping("/topic-papers-graph")
public String papersGraphPage(
        @RequestParam String id,
        @RequestParam String topicName,
        @RequestParam String name,
        Model model) {
    try {
        String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
        String encodedTopic = URLEncoder.encode(topicName, StandardCharsets.UTF_8);

        System.out.println("📘 Generating Paper Graph for Author: " + id +
                " | Topic: " + topicName);

        // Step 1️⃣ Call Graph Service to get papers
        String papersUrl = GRAPH_SERVICE_URL + "papers/by-topic?id=" + encodedId +
                "&topicName=" + encodedTopic;

        Paper[] papers = restTemplate.getForObject(papersUrl, Paper[].class);

        if (papers == null || papers.length == 0) {
            System.out.println("⚠️ No papers found for this topic.");
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", "No Papers Found");
            model.addAttribute("topicName", topicName);
            return "professor-graph-topic-papers";
        }

        // Step 2️⃣ Build graph nodes and edges
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Set<String> addedNodeIds = new HashSet<>();

        // Central node: Professor
        nodes.add(Map.of("data", Map.of(
                "id", id,
                "label", name,
                "type", "prof"
        )));
        addedNodeIds.add(id);

        for (Paper paper : papers) {
            String title = paper.getTitle();
            String nodeId = paper.getId();  // ✅ Use real paper ID
            if (nodeId == null || nodeId.isBlank()) {
                nodeId = title.replaceAll("\\s+", "_").toLowerCase();
            }

            if (!addedNodeIds.contains(nodeId)) {
                nodes.add(Map.of("data", Map.of(
                        "id", nodeId,
                        "label", title,
                        "type", "paper"
                )));
                addedNodeIds.add(nodeId);
            }

            edges.add(Map.of("data", Map.of(
                    "id", id + "-" + nodeId,
                    "source", id,
                    "target", nodeId
            )));
        }

        // Step 3️⃣ Convert to Cytoscape JSON
        ObjectMapper mapper = new ObjectMapper();
        String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

        // Step 4️⃣ Add attributes to model
        model.addAttribute("graphJson", graphJson);
        model.addAttribute("professorName", name);
        model.addAttribute("pageTitle", "Papers in " + topicName);
        model.addAttribute("topicName", topicName);

        System.out.println("✅ Paper graph JSON built successfully for " + topicName);
        return "professor-graph-topic-papers"; // ✅ Update HTML file accordingly

    } catch (Exception e) {
        e.printStackTrace();
        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
        model.addAttribute("professorName", "Error");
        model.addAttribute("topicName", topicName);
        return "professor-graph-topic-papers";
    }
}





}
