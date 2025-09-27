package com.scholarsphere.graphservice.model;

import org.springframework.data.neo4j.core.schema.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Node("Institution")
public class Institution {

    @Id
    private String id; // e.g. "https://openalex.org/I4200000001"

    private String ror;

    private String displayName;

    @Property("display_name_acronyms")
    private List<String> displayNameAcronyms;

    @Property("display_name_alternatives")
    private List<String> displayNameAlternatives;

    private String type;
    private String countryCode;

    // @CompositeProperty // you can also @Relationship to a Geo node
    // private Map<String, Object> geo;

    private String homepageUrl;
    private String imageUrl;
    private String imageThumbnailUrl;

    // International names can be stored as a JSON-ish map property
    @CompositeProperty
    private Map<String, String> international;

    private Boolean isSuperSystem;

    private List<String> lineage;

    private Integer worksCount;
    private Integer citedByCount;

    private String worksApiUrl;

    private LocalDateTime createdDate;
    private LocalDateTime updatedDate;

    // You can store external IDs as a Map property too
    @CompositeProperty
    private Map<String, String> ids;

    // Relationships to other entities
    @Relationship(type = "ASSOCIATED_WITH", direction = Relationship.Direction.OUTGOING)
    private List<Institution> associatedInstitutions;

    // @Relationship(type = "HAS_REPOSITORY", direction = Relationship.Direction.OUTGOING)
    // private List<Repository> repositories;

    // @Relationship(type = "HAS_ROLE", direction = Relationship.Direction.OUTGOING)
    // private List<Role> roles;

    // …getters/setters/constructors…
}
