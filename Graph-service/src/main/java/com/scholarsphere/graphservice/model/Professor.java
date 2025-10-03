package com.scholarsphere.graphservice.model;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Relationship;

import java.util.ArrayList;
import java.util.List;

// @Node("Professor")
@Node("Author")  // Changed label from Professor to Author
public class Professor {

    @Id
    private String id;

    private String displayName;;

    // A professor can author many papers
    @Relationship(type = "AUTHORED")
    private List<Paper> papers = new ArrayList<>();
  

    // --- Constructors ---
    public Professor() {}

    public Professor(String id, String displayName) {
        this.id = id;
        this.displayName = displayName;
    }

    // --- Getters and Setters ---
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getdisplayName() { return displayName; }
    public void setdisplayName(String displayName) { this.displayName = displayName; }

    public List<Paper> getPapers() { return papers; }
    public void setPapers(List<Paper> papers) { this.papers = papers; }
}