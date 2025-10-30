
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

    private String doi;
    // private Integer publicationYear;

    @Relationship(type = "AUTHORED", direction = Relationship.Direction.INCOMING)
    @JsonIgnore
    private List<Professor> authors = new ArrayList<>();

    // --- Constructors ---
    public Paper() {}

    public Paper(String id, String title, String doi) {
        this.id = id;
        this.title = title;
        this.doi = doi;
        //this.publicationYear = publicationYear;
    }

    // --- Getters and Setters ---
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getDoi() { return doi; }
    //public Integer getPublicationYear() { return publicationYear;}

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public void setDoi(String doi) { this.doi = doi; }
    //public void setPublicationYear(Integer publicationYear) { this.publicationYear = publicationYear; }

    // public List<Professor> getAuthors() { return authors; }
    // public void setPapers(List<Professor> authors) { this.authors = authors; }
}
