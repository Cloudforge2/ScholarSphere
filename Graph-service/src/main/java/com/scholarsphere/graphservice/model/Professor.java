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

    private String displayName;

    private boolean fullyIngested = false;  // ✅ new flag

    private int citedByCount;

    private int worksCount;

    private String orcid;

    private String updatedDate;

    private String lastFetched;
    
    private String lastKnownInstitution;

    // @Property("displayNameAlternatives")
    // private List<String> displayNameAlternatives = new ArrayList<>();

    // A professor can author many papers
    @Relationship(type = "AUTHORED", direction = Relationship.Direction.OUTGOING)
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

    public String getDisplayName() { return displayName; }
    public void setDisplayName(String displayName) { this.displayName = displayName; }


    public List<Paper> getPapers() { return papers; }
    public void setPapers(List<Paper> papers) { this.papers = papers; }

    public boolean isFullyIngested() { return fullyIngested; }
    public void setFullyIngested(boolean fullyIngested) { this.fullyIngested = fullyIngested; }

    public int getCitedByCount() { return citedByCount; }
    public void setCitedByCount(int citedByCount) { this.citedByCount = citedByCount; }

    public int getWorksCount() { return worksCount; }
    public void setWorksCount(int worksCount) { this.worksCount = worksCount; }

    public String getOrcid() { return orcid; }
    public void setOrcid(String orcid) { this.orcid = orcid; }

    public String getUpdatedDate() { return updatedDate; }
    public void setUpdatedDate(String updatedDate) { this.updatedDate = updatedDate; }

    public String getLastFetched() { return lastFetched; }
    public void setLastFetched(String lastFetched) { this.lastFetched = lastFetched; }

    public String getLastKnownInstitution() {
        return lastKnownInstitution;
    }
    
    public void setLastKnownInstitution(String lastKnownInstitution) {
        this.lastKnownInstitution = lastKnownInstitution;
    }
    
}