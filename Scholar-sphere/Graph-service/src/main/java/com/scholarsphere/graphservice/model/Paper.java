
package com.scholarsphere.graphservice.model;

import java.util.ArrayList;
import java.util.List;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Relationship;

import com.fasterxml.jackson.annotation.JsonIgnore;

// @Node("Paper")
@Node("Work")  // Changed label from Paper to Work
public class Paper {

    @Id
    private String id;

    private String title;

    @Relationship(type = "AUTHORED", direction = Relationship.Direction.INCOMING)
    @JsonIgnore
    private List<Professor> authors = new ArrayList<>();

    // --- Constructors ---
    public Paper() {}

    public Paper(String id, String title) {
        this.id = id;
        this.title = title;
    }

    // --- Getters and Setters ---
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    // public List<Professor> getAuthors() { return authors; }
    // public void setPapers(List<Professor> authors) { this.authors = authors; }
}
