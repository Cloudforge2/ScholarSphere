package com.scholarsphere.graphservice.model;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Relationship;

import java.util.ArrayList;
import java.util.List;

@Node("Professor")
public class Professor {

    @Id
    private String id;

    private String name;

    // A professor can author many papers
    @Relationship(type = "AUTHORED")
    private List<Paper> papers = new ArrayList<>();

    // --- Constructors ---
    public Professor() {}

    public Professor(String id, String name) {
        this.id = id;
        this.name = name;
    }

    // --- Getters and Setters ---
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public List<Paper> getPapers() { return papers; }
    public void setPapers(List<Paper> papers) { this.papers = papers; }
}
