package com.scholarsphere.graphservice.model;


import org.springframework.data.annotation.Id;
import org.springframework.data.neo4j.core.schema.*;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;


//lombok annotations
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

/**
 * @Data is a shortcut annotation that bundles the features of
 * @Getter, @Setter, @ToString, @EqualsAndHashCode, and @RequiredArgsConstructor
 * all in one.
 *
 * @NoArgsConstructor is often required by frameworks like Spring Data / JPA
 * to create instances of the entity.
 *
 * @AllArgsConstructor creates a constructor with all fields, which can be useful.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Node("Author")
public class Author {

    @Id
    private String id; // OpenAlex ID

    private String displayName;


    private List<String> displayNameAlternatives;

    private String orcid;

 
    private Map<String, String> externalIds; // keys: openalex, scopus, twitter, wikipedia

    private Integer citedByCount;

    private Integer worksCount;

    private String worksApiUrl;

    private LocalDate createdDate;
    private LocalDate updatedDate;

    // @Property("summary_stats")
    // private SummaryStats summaryStats;

    
    private List<CountsByYear> countsByYear;

    // Relationships
    @Relationship(type = "AFFILIATED_WITH",direction = Relationship.Direction.OUTGOING)
    private List<Affiliation> affiliations;

   
    private List<Institution> lastKnownInstitutions=new ArrayList<>();

    // @Relationship(type = "HAS_CONCEPT")
    // private List<ConceptAssociation> concepts; // x_concepts (deprecated)

 

    // public static class SummaryStats {
    //     private Double twoYearMeanCitedness;
    //     private Integer hIndex;
    //     private Integer i10Index;
        
    // }

   


    // @RelationshipProperties
    // public static class ConceptAssociation {
    //     @Id
    //     @GeneratedValue
    //     private Long id;

    //     // @TargetNode
    //     // private Concept concept;

    //     private Double score; // association strength

    // }

//     @Node
//     public static class Concept {
//         @Id
//         private String id;
//         private String displayName;
//         private Integer level;
//         private String wikidata;
//         // Getters and Setters...
//     }

    public static class CountsByYear {
        private Integer year;
        private Integer worksCount;
        private Integer citedByCount;
        // Getters and Setters...
    }
}
