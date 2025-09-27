package com.scholarsphere.graphservice.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.neo4j.core.schema.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
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
@Node("Work")
public class Work {

    @Id
    private String id; // OpenAlex ID
    private String displayName;
    private String title;
    private String doi;
    private LocalDate publicationDate;
    private Integer publicationYear;

    // private Map<String, List<Integer>> abstractInvertedIndex;

    private Integer citedByCount;
    private Float fwci;
    private Float citationNormalizedPercentile;

    private Boolean hasFulltext;
    private String fulltextOrigin;
    private String language;
    private String license;

    private Integer countriesDistinctCount;
    private Integer institutionsDistinctCount;
    private Boolean isParatext;
    private Boolean isRetracted;

    private LocalDateTime createdDate;
    private LocalDateTime updatedDate;

    @Property("ids")
    private Map<String, String> externalIds;

    // Relationships

    @Relationship(type = "AUTHORED_BY", direction = Relationship.Direction.OUTGOING)
    private List<Authorship> authorships;

    @Relationship(type = "RELATED_TO", direction = Relationship.Direction.OUTGOING)
    private List<Work> relatedWorks;

    @Relationship(type = "REFERENCES", direction = Relationship.Direction.OUTGOING)
    private List<Work> referencedWorks;

    // @Relationship(type = "HAS_CONCEPT", direction = Relationship.Direction.OUTGOING)
    // private List<Concept> concepts;

    @Relationship(type = "HAS_INSTITUTION", direction = Relationship.Direction.OUTGOING)
    private List<Institution> correspondingInstitutions;

    @Relationship(type = "HAS_LOCATION", direction = Relationship.Direction.OUTGOING)
    private List<Location> locations;

    @Relationship(type = "PRIMARY_LOCATION", direction = Relationship.Direction.OUTGOING)
    private Location primaryLocation;

    @Relationship(type = "BEST_OA_LOCATION", direction = Relationship.Direction.OUTGOING)
    private Location bestOALocation;

    // @Relationship(type = "HAS_SDG", direction = Relationship.Direction.OUTGOING)
    // private List<SustainableDevelopmentGoal> sustainableDevelopmentGoals;

    // @Relationship(type = "HAS_GRANT", direction = Relationship.Direction.OUTGOING)
    // private List<Grant> grants;

    // @Relationship(type = "COUNT_BY_YEAR", direction = Relationship.Direction.OUTGOING)
    // private List<YearlyCount> countsByYear;

    // @Relationship(type = "HAS_BIBLIO", direction = Relationship.Direction.OUTGOING)
    // private Bibliography biblio;

    // @Relationship(type = "HAS_APC_LIST", direction = Relationship.Direction.OUTGOING)
    // private APC apcList;

    // @Relationship(type = "HAS_APC_PAID", direction = Relationship.Direction.OUTGOING)
    // private APC apcPaid;

    // Getters and setters...
}

// Authorship as a relationship entity
@RelationshipProperties
class Authorship {

    @Id @GeneratedValue
    private Long id;

    @TargetNode
    private Author author;

    private String authorPosition;
    private Boolean isCorresponding;

    @Relationship(type = "AT_INSTITUTION", direction = Relationship.Direction.OUTGOING)
    private List<Institution> institutions;
}

// Example nested entities



class Location {
    @Id
    private String id;
    private String url;
    private String license;
    private String hostType;
    private Boolean isOa;
}


// class Grant {
//     @Id
//     private String id;
//     private String displayName;
// }

// class APC {
//     @Id
//     private String id;
//     private Double price;
//     private String currency;
// }

// class Bibliography {
//     @Id
//     private String id;
//     private String journal;
//     private String volume;
//     private String issue;
//     private String pages;
// }

// class YearlyCount {
//     @Id @GeneratedValue
//     private Long id;
//     private Integer year;
//     private Integer worksCount;
//     private Integer citedByCount;
// }


// class SustainableDevelopmentGoal {
//     @Id
//     private String id;
//     private String name;
// }
