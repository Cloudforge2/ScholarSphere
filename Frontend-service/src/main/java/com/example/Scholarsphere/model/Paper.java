package com.example.Scholarsphere.model;

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
    private String doi;          // FIXED: String, not string
    private int year;
    private String abstractText;

    // Bidirectional link
    private List<Professor> authors;
}
