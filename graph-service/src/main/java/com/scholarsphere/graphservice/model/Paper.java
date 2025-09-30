package com.scholarsphere.graphservice.model;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

// @Node("Paper")
@Node("Work")  // Changed label from Paper to Work
public class Paper {

    @Id
    private String id;

    private String title;

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
}
