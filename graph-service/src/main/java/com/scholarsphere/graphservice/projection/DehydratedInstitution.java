package com.scholarsphere.graphservice.projection;

public interface DehydratedInstitution {

    String getId();
    String getDisplayName();
    String getRor();
    String getType();
    String getCountryCode();
    // lineage would be here too if it's a simple property
    // List<String> getLineage(); 
}