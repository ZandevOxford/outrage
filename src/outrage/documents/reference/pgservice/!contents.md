# outrage.pgservice
0 0 1

## Why it is parsed here rather than handed to libpq
938 938 19

## Three deviations from libpq, all deliberate
1672 1672 34

## Reading, and what comes back
2568 2568 49

## Secrets
3126 3126 58

### outrage.pgservice.ADDED_PARAMETERS *: Mapping[str, str]* *= {'application_name': 'outrage', 'connect_timeout': '5'}*
3557 3557 66

### outrage.pgservice.CONNECTION_PARAMETERS *= frozenset({'application_name', 'channel_binding', 'client_encoding', 'connect_timeout', 'dbname', 'fallback_application_name', 'gssdelegation', 'gssencmode', 'gsslib', 'host', 'hostaddr', 'keepalives', 'keepalives_count', 'keepalives_idle', 'keepalives_interval', 'krbsrvname', 'load_balance_hosts', 'options', 'passfile', 'password', 'port', 'replication', 'require_auth', 'requirepeer', 'ssl_max_protocol_version', 'ssl_min_protocol_version', 'sslcert', 'sslcertmode', 'sslcompression', 'sslcrl', 'sslcrldir', 'sslkey', 'sslmode', 'sslnegotiation', 'sslpassword', 'sslrootcert', 'sslsni', 'target_session_attrs', 'tcp_user_timeout', 'user'})*
4106 4106 73

### outrage.pgservice.DEFAULT_SERVICE *= 'outrage'*
5302 5302 84

### outrage.pgservice.NESTED_PARAMETER *= 'service'*
5589 5589 91

### outrage.pgservice.NO_DEFAULT_SECTION *= '\\x00'*
5802 5802 97

### outrage.pgservice.PATH_PARAMETERS *= frozenset({'passfile', 'sslcert', 'sslcrl', 'sslcrldir', 'sslkey', 'sslrootcert'})*
6166 6166 105

### outrage.pgservice.REDACTION *= '(not shown)'*
6570 6570 112

### *class* outrage.pgservice.Resolution(service: Service | None = None, refusals: tuple[Refusal, ...] = (), searched: tuple[Path, ...] = ())
6823 6823 118

#### service *: Service | None*
7628 7628 128

#### refusals *: tuple[Refusal, ...]*
7863 7863 132

#### searched *: tuple[Path, ...]*
8060 8060 136

### outrage.pgservice.SECRET_PARAMETERS *= frozenset({'password', 'sslpassword'})*
8291 8291 140

### outrage.pgservice.SERVICE_FILE_VARIABLE *= 'PGSERVICEFILE'*
8505 8505 145

### outrage.pgservice.SYSCONF_VARIABLE *= 'PGSYSCONFDIR'*
8716 8716 150

### outrage.pgservice.SYSTEM_FILE_NAME *= 'pg_service.conf'*
8914 8914 155

### outrage.pgservice.SYSTEM_TRUST_STORE *= 'system'*
9142 9142 160

### *class* outrage.pgservice.Service(name: str, path: Path, parameters: Mapping[str, str])
9326 9326 165

#### name *: str*
10110 10110 175

#### path *: Path*
10229 10229 179

#### parameters *: Mapping[str, str]*
10348 10348 183

#### *property* redacted *: dict[str, str]*
10653 10653 187

#### *property* holds_secret *: bool*
11133 11133 195

### outrage.pgservice.USER_FILE_NAME *= '.pg_service.conf'*
11500 11500 203

### outrage.pgservice.candidates(file: str | PathLike[str] | None = None, \*, environ: Mapping[str, str] | None = None) → tuple[Path, ...]
11619 11619 207

### outrage.pgservice.resolve(file: str | PathLike[str] | None = None, service: str = DEFAULT_SERVICE, \*, environ: Mapping[str, str] | None = None) → Resolution
13094 13096 222
