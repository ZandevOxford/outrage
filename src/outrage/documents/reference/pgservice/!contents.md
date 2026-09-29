# outrage.pgservice
0 0 1

## Why it is parsed here rather than handed to libpq
1069 1069 21

## Three deviations from libpq, all deliberate
1803 1803 36

## Reading, and what comes back
2699 2699 51

## Secrets
3257 3257 60

### outrage.pgservice.ADDED_PARAMETERS *: Mapping[str, str]* *= {'application_name': 'outrage', 'connect_timeout': '5'}*
3688 3688 68

### outrage.pgservice.CONNECTION_PARAMETERS *= frozenset({'application_name', 'channel_binding', 'client_encoding', 'connect_timeout', 'dbname', 'fallback_application_name', 'gssdelegation', 'gssencmode', 'gsslib', 'host', 'hostaddr', 'keepalives', 'keepalives_count', 'keepalives_idle', 'keepalives_interval', 'krbsrvname', 'load_balance_hosts', 'options', 'passfile', 'password', 'port', 'replication', 'require_auth', 'requirepeer', 'ssl_max_protocol_version', 'ssl_min_protocol_version', 'sslcert', 'sslcertmode', 'sslcompression', 'sslcrl', 'sslcrldir', 'sslkey', 'sslmode', 'sslnegotiation', 'sslpassword', 'sslrootcert', 'sslsni', 'target_session_attrs', 'tcp_user_timeout', 'user'})*
4237 4237 75

### outrage.pgservice.DEFAULT_SERVICE *= 'outrage'*
5433 5433 86

### outrage.pgservice.NESTED_PARAMETER *= 'service'*
5720 5720 93

### outrage.pgservice.NO_DEFAULT_SECTION *= '\\x00'*
5933 5933 99

### outrage.pgservice.PATH_PARAMETERS *= frozenset({'passfile', 'sslcert', 'sslcrl', 'sslcrldir', 'sslkey', 'sslrootcert'})*
6297 6297 107

### outrage.pgservice.REDACTION *= '(not shown)'*
6701 6701 114

### *class* outrage.pgservice.Resolution(service: Service | None = None, refusals: tuple[Refusal, ...] = (), searched: tuple[Path, ...] = ())
6954 6954 120

#### service *: Service | None*
7759 7759 130

#### refusals *: tuple[Refusal, ...]*
7994 7994 134

#### searched *: tuple[Path, ...]*
8191 8191 138

### outrage.pgservice.SECRET_PARAMETERS *= frozenset({'password', 'sslpassword'})*
8422 8422 142

### outrage.pgservice.SERVICE_FILE_VARIABLE *= 'PGSERVICEFILE'*
8636 8636 147

### outrage.pgservice.SYSCONF_VARIABLE *= 'PGSYSCONFDIR'*
8847 8847 152

### outrage.pgservice.SYSTEM_FILE_NAME *= 'pg_service.conf'*
9045 9045 157

### outrage.pgservice.SYSTEM_TRUST_STORE *= 'system'*
9273 9273 162

### *class* outrage.pgservice.Service(name: str, path: Path, parameters: Mapping[str, str])
9457 9457 167

#### name *: str*
10241 10241 177

#### path *: Path*
10360 10360 181

#### parameters *: Mapping[str, str]*
10479 10479 185

#### *property* redacted *: dict[str, str]*
10784 10784 189

#### *property* holds_secret *: bool*
11264 11264 197

### outrage.pgservice.USER_FILE_NAME *= '.pg_service.conf'*
11631 11631 205

### outrage.pgservice.candidates(file: str | PathLike[str] | None = None, \*, environ: Mapping[str, str] | None = None) → tuple[Path, ...]
11750 11750 209

### outrage.pgservice.resolve(file: str | PathLike[str] | None = None, service: str = DEFAULT_SERVICE, \*, environ: Mapping[str, str] | None = None) → Resolution
13225 13227 224
