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
    private String venue;           // add this
    private int year;               // add this
    private String abstractText;    // add this

    // To support bidirectional link in controllers
    private List<Professor> authors;
}
