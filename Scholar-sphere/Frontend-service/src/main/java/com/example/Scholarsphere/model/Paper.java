package com.example.Scholarsphere.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Paper {
    private String id;
    private String title;
    private String venue;
    private int year;

    // Match "abstract" from JSON to "abstractText" in Java
    @JsonProperty("abstract")
    private String abstractText;

    // If API returns citation count (add if you need it)
    private int citations;

    // List of co-authors (optional, can be null)
    private List<Professor> authors;
}
