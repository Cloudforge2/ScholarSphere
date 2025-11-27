package com.example.Scholarsphere.controller;

import com.example.Scholarsphere.DTO.TopicStat;
import com.example.Scholarsphere.model.Paper;
import com.example.Scholarsphere.model.Professor;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.client.RestTemplate;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Controller
public class ProfessorGraphController {

    private final RestTemplate restTemplate;

    // Updated gateway service base URL for "by-name" endpoint

    private static final String PROFESSOR_BY_ID_URL = "http://summary-service:8085/professors/summary/by-id?id=";
    private static final String PAPER_BY_TITLE_URL = "http://summary-service:8085/papers/by-title?title=";
    private static final String FETCH_AUTHOR_BY_ID_URL = "http://scrappy:8083/api/fetch-author-by-id?id=";
    private static final String GRAPH_SERVICE_URL = "http://graph-service:8082/api/professors/";
    


    public ProfessorGraphController() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(2000);   // fail fast if backend is down
        factory.setReadTimeout(40000);      // allow Scrappy to fetch OpenAlex
        this.restTemplate = new RestTemplate(factory);
    }

    // Endpoint to fetch professor graph by name
@GetMapping("/professor-graph")
public String professorGraphPage(@RequestParam String id, Model model) {
    try {
        String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);

        // Step 1️⃣ Check if author should be ingested in Neo4j
        String shouldIngestUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
        Boolean shouldIngest = restTemplate.getForObject(shouldIngestUrl, Boolean.class);

        if (Boolean.TRUE.equals(shouldIngest)) {
            System.out.println("🟠 Author not found or not fully ingested, triggering Scrappy...");
            String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
            restTemplate.getForObject(fetchUrl, String.class);
            Thread.sleep(3000);
        }

        // Step 2️⃣ Fetch graph data
        String graphUrl = GRAPH_SERVICE_URL + encodedId + "/graph";
        Professor prof = restTemplate.getForObject(graphUrl, Professor.class);

        if (prof == null) {
            throw new RuntimeException("Graph service returned null professor for ID: " + id);
        }

        // Step 3️⃣ Build nodes + edges
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Set<String> addedNodeIds = new HashSet<>();

        nodes.add(Map.of("data", Map.of(
                "id", prof.getId(),
                "label", prof.getDisplayName(),
                "type", "prof"
        )));
        addedNodeIds.add(prof.getId());

        if (prof.getPapers() != null) {
            for (Paper paper : prof.getPapers()) {

                if (!addedNodeIds.contains(paper.getId())) {
                    nodes.add(Map.of("data", Map.of(
                            "id", paper.getId(),
                            "label", paper.getTitle(),
                            "type", "paper"
                    )));
                    addedNodeIds.add(paper.getId());
                }

                edges.add(Map.of("data", Map.of(
                        "id", prof.getId() + "-" + paper.getId(),
                        "source", prof.getId(),
                        "target", paper.getId()
                )));

                if (paper.getAuthors() != null) {
                    for (Professor coauthor : paper.getAuthors()) {
                        if (coauthor.getId().equals(prof.getId())) continue;

                        if (!addedNodeIds.contains(coauthor.getId())) {
                            nodes.add(Map.of("data", Map.of(
                                    "id", coauthor.getId(),
                                    "label", coauthor.getDisplayName(),
                                    "type", "coauthor"
                            )));
                            addedNodeIds.add(coauthor.getId());
                        }

                        edges.add(Map.of("data", Map.of(
                                "id", coauthor.getId() + "-" + paper.getId(),
                                "source", coauthor.getId(),
                                "target", paper.getId()
                        )));
                    }
                }
            }
        }

        ObjectMapper mapper = new ObjectMapper();
        String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

        // --- ADD TO MODEL ---
        model.addAttribute("graphJson", graphJson);
        model.addAttribute("professorName", prof.getDisplayName());
        model.addAttribute("profId", prof.getId());   // ⭐⭐ REQUIRED FOR BUTTONS ⭐⭐
        model.addAttribute("paperCount", prof.getPapers() != null ? prof.getPapers().size() : 0);

        return "professor-graph";

    } catch (Exception graphEx) {

        model.addAttribute("error",
                "Unable to load professor graph because a backend service is unavailable.");
        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
        model.addAttribute("professorName", "Unavailable");
        model.addAttribute("profId", id);   // still pass id so buttons do not break
        model.addAttribute("paperCount", 0);

        return "professor-graph";
    }
}


    

@GetMapping("/professor-summary")
public String professorSummary(@RequestParam String id, Model model) {
    try {
        // 1️⃣ Fetch author name + ORCID from graph-service
        String graphUrl = GRAPH_SERVICE_URL + URLEncoder.encode(id, StandardCharsets.UTF_8) + "/graph";
        Professor prof = restTemplate.getForObject(graphUrl, Professor.class);

        if (prof == null) {
            throw new RuntimeException("Graph service returned null professor for ID: " + id);
        }

        model.addAttribute("author", prof.getDisplayName());
        model.addAttribute("orcid", prof.getOrcid() != null ? prof.getOrcid() : "N/A");

        // 2️⃣ Fetch summary from summary-service
        String url = PROFESSOR_BY_ID_URL + id;
        System.out.println("DEBUG: Calling summary service URL: " + url);

        Map<String, Object> profMap = restTemplate.getForObject(url, Map.class);
        System.out.println("DEBUG: Raw response from summary service: " + profMap);

        if (profMap == null || profMap.isEmpty()) {
            throw new RuntimeException("Summary service returned empty response for ID: " + id);
        }

        // 3️⃣ Extract and parse raw summary
        String rawSummary = (String) profMap.getOrDefault("research_summary", "");
        List<Map<String, String>> sections = new ArrayList<>();

        // Split on ANY blank line (Windows \r\n\r\n OR Linux \n\n)
        String[] blocks = rawSummary.split("\\r?\\n\\s*\\r?\\n");

        Pattern pattern = Pattern.compile("\\*\\*(.*?)\\*\\*:\\s*(.*)", Pattern.DOTALL);

        for (String block : blocks) {
            block = block.trim();
            if (block.isEmpty()) continue;

            Matcher matcher = pattern.matcher(block);

            if (matcher.matches()) {
                String heading = matcher.group(1).trim();
                String body = matcher.group(2).trim();

                Map<String, String> map = new HashMap<>();
                map.put("heading", heading);
                map.put("body", body);
                sections.add(map);

            } else {
                // fallback block → treat as normal paragraph
                Map<String, String> map = new HashMap<>();
                map.put("heading", "");
                map.put("body", block);
                sections.add(map);
            }
        }

        model.addAttribute("sections", sections);

        // 4️⃣ Additional fields from summary-service
        model.addAttribute("papers_analyzed_count", profMap.getOrDefault("papers_analyzed_count", "N/A"));
        model.addAttribute("papers_sample", profMap.getOrDefault("papers_sample", Collections.emptyList()));

    } catch (Exception e) {
        System.err.println("ERROR: Could not fetch summary for professor ID " + id + ": " + e.getMessage());
        e.printStackTrace();

        model.addAttribute("error", "Could not fetch summary for professor with ID: " + id);
        model.addAttribute("author", "Unknown Professor");
        model.addAttribute("orcid", "N/A");
    }

    return "professor-summary";
}

    

    @GetMapping("/coauthor-graph")
public String coauthorGraphPage(@RequestParam String id, Model model) {
    try {
        String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
        System.out.println("👥 Generating Coauthor Graph for: " + id);

        // Step 1️⃣ Check if we must ingest
        String shouldIngestUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
        Boolean shouldIngest = restTemplate.getForObject(shouldIngestUrl, Boolean.class);

        if (Boolean.TRUE.equals(shouldIngest)) {
            System.out.println("🟠 Author not found or outdated — triggering Scrappy...");
            String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
            restTemplate.getForObject(fetchUrl, String.class);
            Thread.sleep(3000);
        }

        // Step 2️⃣ Fetch professor info (required for name + id)
        String graphUrl = GRAPH_SERVICE_URL + encodedId + "/graph";
        Professor prof = restTemplate.getForObject(graphUrl, Professor.class);

        if (prof == null) {
            throw new RuntimeException("Graph returned null professor for ID: " + id);
        }

        String profId = prof.getId();
        String profName = prof.getDisplayName();

        // Step 3️⃣ Fetch coauthors
        String coauthorUrl = GRAPH_SERVICE_URL + "coauthors?id=" + encodedId;
        Professor[] coauthors = restTemplate.getForObject(coauthorUrl, Professor[].class);

        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Set<String> addedNodeIds = new HashSet<>();

        // Add main professor node
        nodes.add(Map.of("data", Map.of(
                "id", profId,
                "label", profName,
                "type", "prof"
        )));
        addedNodeIds.add(profId);

        // Coauthors
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
                        "id", profId + "-" + co.getId(),
                        "source", profId,
                        "target", co.getId()
                )));
            }
        }

        ObjectMapper mapper = new ObjectMapper();
        String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

        // ⭐⭐⭐ ADD SAME ATTRIBUTES AS PAPER GRAPH ⭐⭐⭐
        model.addAttribute("graphJson", graphJson);
        model.addAttribute("profId", profId);            // required for header buttons
        model.addAttribute("professorName", profName);  // required for header buttons
        model.addAttribute("paperCount", 0);            // not used, but consistent

        return "professor-graph-coauthor";

    } catch (Exception ex) {

        ex.printStackTrace();

        model.addAttribute("error",
                "Unable to load coauthor graph because backend service is unavailable.");

        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
        model.addAttribute("profId", id);     // still send something so buttons don't break
        model.addAttribute("professorName", "Unavailable");

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
                System.out.println("DEBUG: DOI fetched = " + paper.getDoi());

            } else {
                throw new RuntimeException("No paper found for title: " + title);
            }

        } else {
            throw new IllegalArgumentException("Either 'title' or 'id' parameter is required.");
        }


        // 2️⃣ Fetch paper summary from Summary Service (FastAPI)
        String summaryText = "";
        try {
            String summaryUrl;

            if (paperId != null) {
                summaryUrl = "http://summary-service:8085/paper/by-id?paper_id=" + paperId;
            } else {
                summaryUrl = "http://summary-service:8085/paper/by-title?title=" +
                        URLEncoder.encode(title, StandardCharsets.UTF_8);
            }

            System.out.println("DEBUG: Fetching paper summary from: " + summaryUrl);

            Map<String, Object> summaryMap = restTemplate.getForObject(summaryUrl, Map.class);
            if (summaryMap != null) {

    // 1️⃣ Summary text
    summaryText = (String) summaryMap.getOrDefault("summary", "No summary available.");

    // print raw summary
    System.out.println("\n================ SUMMARY RESPONSE ================");
    System.out.println(summaryText);
    System.out.println("=================================================\n");

    // 2️⃣ Extract paper_info fields (including DOI)
    Object paperInfoObj = summaryMap.get("paper_info");
    if (paperInfoObj instanceof Map<?, ?> info) {

        if (info.get("doi") != null) {
            paper.setDoi((String) info.get("doi"));
            System.out.println("DEBUG: DOI received = " + paper.getDoi());
        }

        if (info.get("year") != null) {
            paper.setYear((Integer) info.get("year"));
        }

        if (info.get("venue") != null) {
            paper.setVenue((String) info.get("venue"));
        }

        if (info.get("abstract") != null) {
            paper.setAbstractText((String) info.get("abstract"));
        }
    }

} else {
    System.err.println("⚠️ No summary found for paper ID: " + paperId);
    summaryText = "No summary available.";
}


        } catch (Exception e) {
            System.err.println("⚠️ Could not fetch summary: " + e.getMessage());
            summaryText = "Summary unavailable — please try again later.";
        }


        // 3️⃣ Split summary into sections for HTML
        List<Map<String, String>> sections = new ArrayList<>();

        String[] parts = summaryText.split("##");
        Pattern pattern = Pattern.compile("^\\s*([A-Za-z0-9()\\-/ ]+?)\\s+(.*)$", Pattern.DOTALL);

        for (String part : parts) {
            part = part.trim();
            if (part.isEmpty()) continue;

            Matcher m = pattern.matcher(part);

            if (m.matches()) {
                sections.add(Map.of(
                        "heading", m.group(1).trim(),
                        "body", m.group(2).trim()
                ));
            } else {
                sections.add(Map.of(
                        "heading", "",
                        "body", part.trim()
                ));
            }
        }

        model.addAttribute("sections", sections);


        // 4️⃣ Fetch authors from graph-service
        Professor[] authors = null;

        try {
            String authorsUrl = GRAPH_SERVICE_URL + "paper/authors?id=" +
                    URLEncoder.encode(paperId, StandardCharsets.UTF_8);

            System.out.println("DEBUG: Fetching authors from URL: " + authorsUrl);
            authors = restTemplate.getForObject(authorsUrl, Professor[].class);

            System.out.println("DEBUG: Authors fetched: " + (authors != null ? authors.length : 0));

        } catch (Exception graphEx) {
            System.err.println("❌ Graph-service unavailable (paper authors)");
            model.addAttribute("error", "Author graph is unavailable right now.");
        }


        // 5️⃣ Construct Graph Data
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();

        // paper node
        nodes.add(Map.of("data", Map.of(
                "id", paperId,
                "label", paper.getTitle(),
                "type", "paper"
        )));

        // author nodes
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


        // 6️⃣ Add data to HTML model
        model.addAttribute("graphJson", graphJson);
        model.addAttribute("paper", paper);
        model.addAttribute("title", paper.getTitle());
        model.addAttribute("paperId", paperId);

        // ⭐ NEW: Add DOI to model
        model.addAttribute("doi", paper.getDoi());

    } catch (Exception e) {
        e.printStackTrace();
        model.addAttribute("title", title != null ? title : "Unknown Paper");
        model.addAttribute("summary", "Could not fetch data: " + e.getMessage());
        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
    }

    return "paper-summary";
}



    @GetMapping("/topic-graph")
public String topicGraphPage(@RequestParam String id,
                             @RequestParam String name,
                             Model model) {
    try {
        String encodedId = URLEncoder.encode(id, StandardCharsets.UTF_8);
        System.out.println("🌐 Generating Research Topic Graph for: " + id);

        // Step 1️⃣ Check if author exists
        String shouldIngestUrl = GRAPH_SERVICE_URL + "exists/" + encodedId;
        Boolean shouldIngest = restTemplate.getForObject(shouldIngestUrl, Boolean.class);

        if (Boolean.TRUE.equals(shouldIngest)) {
            System.out.println("🟠 Author not found or outdated — triggering Scrappy...");
            String fetchUrl = FETCH_AUTHOR_BY_ID_URL + encodedId;
            restTemplate.getForObject(fetchUrl, String.class);
            Thread.sleep(3000);
        }

        // Step 2️⃣ Fetch topics
        String topicUrl = GRAPH_SERVICE_URL + "topics?id=" + encodedId;
        TopicStat[] topics = restTemplate.getForObject(topicUrl, TopicStat[].class);

        if (topics == null || topics.length == 0) {
            System.out.println("⚠️ No topics found for this professor");
            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", name);
            model.addAttribute("profId", id);
            return "professor-graph-topic";
        }

        // Step 3️⃣ Build graph nodes and edges
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Set<String> addedNodeIds = new HashSet<>();

        // Add professor node
        nodes.add(Map.of("data", Map.of(
                "id", id,
                "label", name,
                "type", "prof"
        )));
        addedNodeIds.add(id);

        // Add topic nodes
        for (TopicStat topic : topics) {
            String nodeId = topic.getTopic().replaceAll("\\s+", "_");

            if (!addedNodeIds.contains(nodeId)) {
                nodes.add(Map.of("data", Map.of(
                        "id", nodeId,
                        "label", topic.getTopic(),
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

        // Convert to JSON
        ObjectMapper mapper = new ObjectMapper();
        String graphJson = mapper.writeValueAsString(Map.of("nodes", nodes, "edges", edges));

        // ⭐⭐⭐ SAME ATTRIBUTES AS OTHER GRAPH PAGES ⭐⭐⭐
        model.addAttribute("graphJson", graphJson);
        model.addAttribute("professorName", name);   // for header
        model.addAttribute("profId", id);            // for header buttons
        model.addAttribute("paperCount", 0);         // consistent attribute

        System.out.println("✅ Topic graph JSON built successfully");

        return "professor-graph-topic";

    } catch (Exception ex) {

        ex.printStackTrace();

        model.addAttribute("error",
                "Unable to load research topics because a backend service is unavailable.");

        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
        model.addAttribute("professorName", "Unavailable");
        model.addAttribute("profId", id);  // still pass whatever we have

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

        // Step 1️⃣ Fetch papers from graph-service
        String papersUrl = GRAPH_SERVICE_URL + "papers/by-topic?id=" + encodedId +
                "&topicName=" + encodedTopic;

        Paper[] papers = restTemplate.getForObject(papersUrl, Paper[].class);

        if (papers == null || papers.length == 0) {
            System.out.println("⚠️ No topic papers found");

            model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
            model.addAttribute("professorName", name);
            model.addAttribute("profId", id);
            model.addAttribute("topicName", topicName);
            model.addAttribute("paperCount", 0);

            return "professor-graph-topic-papers";
        }

        // Step 2️⃣ Build graph nodes + edges
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Set<String> addedNodeIds = new HashSet<>();

        // Central professor node
        nodes.add(Map.of("data", Map.of(
                "id", id,
                "label", name,
                "type", "prof"
        )));
        addedNodeIds.add(id);

        for (Paper paper : papers) {

            String nodeId = paper.getId();
            if (nodeId == null || nodeId.isBlank()) {
                nodeId = paper.getTitle().replaceAll("\\s+", "_").toLowerCase();
            }

            if (!addedNodeIds.contains(nodeId)) {
                nodes.add(Map.of("data", Map.of(
                        "id", nodeId,
                        "label", paper.getTitle(),
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

        // Step 3️⃣ Convert to JSON
        ObjectMapper mapper = new ObjectMapper();
        String graphJson = mapper.writeValueAsString(
                Map.of("nodes", nodes, "edges", edges)
        );

        // Step 4️⃣ Set model attributes (SAME AS OTHER GRAPH PAGES)
        model.addAttribute("graphJson", graphJson);
        model.addAttribute("professorName", name);   // used in header
        model.addAttribute("profId", id);            // used in button URLs
        model.addAttribute("topicName", topicName);
        model.addAttribute("paperCount", papers.length); // for consistency

        System.out.println("✅ Built paper graph for topic: " + topicName);

        return "professor-graph-topic-papers";

    } catch (Exception ex) {

        ex.printStackTrace();

        model.addAttribute("error",
                "Unable to load topic papers because a backend service is unavailable.");

        model.addAttribute("graphJson", "{\"nodes\":[],\"edges\":[]}");
        model.addAttribute("professorName", "Unavailable");
        model.addAttribute("profId", id);
        model.addAttribute("topicName", topicName);
        model.addAttribute("paperCount", 0);

        return "professor-graph-topic-papers";
    }
}



}
