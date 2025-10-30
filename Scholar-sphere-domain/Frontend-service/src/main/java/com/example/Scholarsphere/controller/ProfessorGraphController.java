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
   
    private static final String PROFESSOR_BY_NAME_URL = "http://summary-service:8085/professors/summary/by-name?name=";
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
        // Encode the author name for the URL
        String url = PROFESSOR_BY_NAME_URL + URLEncoder.encode(name, StandardCharsets.UTF_8);
        System.out.println("DEBUG: Calling summary service URL: " + url);

        // Fetch JSON response from FastAPI
        Map<String, Object> profMap = restTemplate.getForObject(url, Map.class);
        System.out.println("DEBUG: Raw response from summary service: " + profMap);

        if (profMap == null || profMap.isEmpty()) {
            throw new RuntimeException("No professor found for name: " + name);
        }

        // Populate model attributes for Thymeleaf
        model.addAttribute("author", profMap.getOrDefault("author", "Unknown"));
        model.addAttribute("affiliation", profMap.getOrDefault("affiliation", "Unknown"));
        model.addAttribute("total_publications", profMap.getOrDefault("total_publications", "N/A"));
        model.addAttribute("citation_count", profMap.getOrDefault("citation_count", "N/A"));
        model.addAttribute("h_index", profMap.getOrDefault("h_index", "N/A"));
        model.addAttribute("summary", profMap.getOrDefault("summary", "No summary available."));
        model.addAttribute("key_research_areas", profMap.getOrDefault("key_research_areas", Collections.emptyList()));

    } catch (Exception e) {
        System.err.println("ERROR: Could not fetch data for " + name + ": " + e.getMessage());
        e.printStackTrace();

        // Pass error message to template
        model.addAttribute("error", "Could not fetch data for " + name + ": " + e.getMessage());
        model.addAttribute("author", null);
    }

    // Return Thymeleaf template
    return "professor-summary";
}

    /** ---------------------- PAPER SUMMARY ---------------------- */
    // @GetMapping("/paper-summary")
    // public String paperSummary(@RequestParam String title, Model model) {
    //     try {
    //         String url = PAPER_BY_TITLE_URL + URLEncoder.encode(title, StandardCharsets.UTF_8);
    //         Paper[] papers = restTemplate.getForObject(url, Paper[].class);

    //         if (papers == null || papers.length == 0) {
    //             throw new RuntimeException("No paper found for title: " + title);
    //         }

    //         Paper paper = papers[0];
    //         model.addAttribute("title", paper.getTitle());
    //         model.addAttribute("summary", "Paper '" + paper.getTitle() + "' has " +
    //                 (paper.getAuthors() != null ? paper.getAuthors().size() : 0) + " authors.");

    //     } catch (Exception e) {
    //         model.addAttribute("title", title);
    //         model.addAttribute("summary", "Could not fetch data for " + title + ": " + e.getMessage());
    //     }

    //     return "paper-summary";
    // }

    @GetMapping("/coauthor-graph")
    public String coauthorGraphPage(@RequestParam String id, Model model) {
        try {
            String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
            System.out.println("👥 Generating Coauthor Graph for: " + id);

            // Check existence
            String existsUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
            Boolean exists = restTemplate.getForObject(existsUrl, Boolean.class);

            if (exists == null || !exists) {
                System.out.println("🟠 Author not found, triggering Scrappy...");
                restTemplate.getForObject(FETCH_AUTHOR_BY_ID_URL + encodedId, String.class);
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
        // 1️⃣ Determine which input to use
        if (id != null && !id.isEmpty()) {
            // Direct paper ID provided — skip title lookup
            paperId = id;
            System.out.println("✅ Using provided paper ID: " + paperId);
            paper.setId(paperId);
            paper.setTitle(title != null ? title : "Unknown Paper");
        } else if (title != null && !title.isEmpty()) {
            // Lookup paper ID via title as before
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

        // 2️⃣ Fetch paper→authors graph from graph-service
        String authorsUrl = GRAPH_SERVICE_URL + "paper/authors?id=" +
                URLEncoder.encode(paperId, StandardCharsets.UTF_8);
        System.out.println("DEBUG: Fetching authors from URL: " + authorsUrl);

        Professor[] authors = restTemplate.getForObject(authorsUrl, Professor[].class);
        System.out.println("DEBUG: Authors fetched: " + (authors != null ? authors.length : 0));

        // 3️⃣ Build Cytoscape-style JSON
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();

        // Add paper node
        nodes.add(Map.of("data", Map.of(
                "id", paperId,
                "label", paper.getTitle(),
                "type", "paper"
        )));

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

        ObjectMapper mapper = new ObjectMapper();
        String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

        // 4️⃣ Add data to model
        model.addAttribute("graphJson", graphJson);
        model.addAttribute("paper", paper);
        model.addAttribute("title", paper.getTitle());
        model.addAttribute("summary", "Visualization for paper '" + paper.getTitle() + "' and its authors.");

    } catch (Exception e) {
        e.printStackTrace();
        model.addAttribute("title", title != null ? title : "Unknown Paper");
        model.addAttribute("summary", "Could not fetch data: " + e.getMessage());
        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
    }

    return "paper-summary";
}


    @GetMapping("/subfield-graph")
    public String subfieldGraphPage(@RequestParam String id,@RequestParam String name, Model model) {
        try {
            String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
            System.out.println("🌐 Generating Research Domain Graph for: " + id);

            // Step 1️⃣ Check if author exists
            String existsUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
            Boolean exists = restTemplate.getForObject(existsUrl, Boolean.class);

            if (exists == null || !exists) {
                System.out.println("🟠 Author not found, triggering Scrappy...");
                restTemplate.getForObject(FETCH_AUTHOR_BY_ID_URL + encodedId, String.class);
                Thread.sleep(3000);
            }

            // Step 2️⃣ Fetch subfields of this author
            String subfieldUrl = GRAPH_SERVICE_URL + "subfields?id=" + encodedId;

            String[] subfields = restTemplate.getForObject(subfieldUrl, String[].class);

            if (subfields == null || subfields.length == 0) {
                System.out.println("⚠️ No subfields found for author " + id);
                model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
                model.addAttribute("professorName", "No Research Domains Found");
                return "professor-graph-subfield";
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

            // Add subfield nodes and edges
            for (String subfield : subfields) {
                String nodeId = subfield.replaceAll("\\s+", "_");

                if (!addedNodeIds.contains(nodeId)) {
                    nodes.add(Map.of("data", Map.of(
                            "id", nodeId,
                            "label", subfield,
                            "type", "subfield"
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
            System.out.println("✅ Subfield graph JSON: " + graphJson);

            return "professor-graph-subfield"; // create this HTML page below

        } catch (Exception e) {
            e.printStackTrace();
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", "Error");
            return "professor-graph-subfield";
        }
    }

    @GetMapping("/domain-papers-graph")
    public String papersGraphPage(
            @RequestParam String id,
            @RequestParam String subfieldName,
            @RequestParam String name,
            Model model) {
        try {
            String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
            String encodedSubfield = URLEncoder.encode(subfieldName, StandardCharsets.UTF_8);

            System.out.println("📘 Generating Paper Graph for Author: " + id +
                            " | Subfield: " + subfieldName);

            // Step 1️⃣ Call Graph Service to get papers
            String papersUrl = GRAPH_SERVICE_URL + "papers/by-subfield?id=" + encodedId +
                            "&subfieldName=" + encodedSubfield;

            Paper[] papers = restTemplate.getForObject(papersUrl, Paper[].class);

            if (papers == null || papers.length == 0) {
                System.out.println("⚠️ No papers found for this subfield.");
                model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
                model.addAttribute("professorName", "No Papers Found");
                model.addAttribute("subfieldName", subfieldName);
                return "professor-graph-papers";
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

            // Paper nodes
            for (Paper paper : papers) {
                String title = paper.getTitle();
                String nodeId = title.replaceAll("\\s+", "_").toLowerCase();

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
            model.addAttribute("pageTitle", "Papers in " + subfieldName);
            model.addAttribute("subfieldName", subfieldName);


            System.out.println("✅ Paper graph JSON built successfully for " + subfieldName);
            return "professor-graph-domain-papers"; 

        } catch (Exception e) {
            e.printStackTrace();
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", "Error");
            model.addAttribute("subfieldName", subfieldName);
            return "professor-graph-domain-papers";
        }
    }




}
