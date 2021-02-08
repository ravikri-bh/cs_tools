CREATE DATABASE cs_tools;
USE cs_tools;


CREATE TABLE introspect_user (
      name         VARCHAR(255)
    , display_name VARCHAR(255)
    , email        VARCHAR(255)
    , created      DATETIME
    , modified     DATETIME
);

ALTER TABLE introspect_user ADD CONSTRAINT PRIMARY KEY (name);


CREATE TABLE introspect_group (
      name         VARCHAR(255)
    , display_name VARCHAR(255)
    , description  VARCHAR(255)
    , created      DATETIME
    , modified     DATETIME
);

ALTER TABLE introspect_group ADD CONSTRAINT PRIMARY KEY (name);


CREATE TABLE asso_introspect_user_group (
      user_name  VARCHAR(255)
    , group_name VARCHAR(255)
);

ALTER TABLE asso_introspect_user_group ADD CONSTRAINT PRIMARY KEY (user_name, group_name);
ALTER TABLE asso_introspect_user_group ADD CONSTRAINT "FK_user_name" FOREIGN KEY ("user_name") REFERENCES "introspect_user" ("name");
ALTER TABLE asso_introspect_user_group ADD CONSTRAINT "FK_group_name" FOREIGN KEY ("group_name") REFERENCES "introspect_group" ("name");
