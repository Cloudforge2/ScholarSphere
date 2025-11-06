package com.example.Scholarsphere.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Professor {
    private String id;
    private String displayName; // Matches controller usage
    private List<Paper> papers; // List of papers authored by this professor
    private boolean fullyIngested;
    private int citedByCount;
    private int worksCount;
    private String orcid;
    private String lastKnownInstitution;

}
