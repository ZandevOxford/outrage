# Home store

This is the default home-store readme. Ask the user whether they want different
conventions, and update `home/readme` if they do.

This writable store is shared by every Outrage project for this user. Keep
durable user-wide knowledge here, and keep project-specific state and decisions
in each project's root store. Changes here affect every project session.

Give every document a title. Keep routing documents short, and add information
as it becomes durable rather than collecting it only at the end of a session.

## Suggested structure

Create these documents as they become useful:

* `home/readme`: the conventions for this shared store. Every session is told
  to read it, so keep it mostly static.
* `home/contents`: a short index routing to user-wide documents that are not
  obvious from a title survey.
* `home/agents`: agents and skills that are useful across projects.
* `home/reference`: durable facts and working practices that apply across
  projects. Use child documents to keep separate subjects separate.
