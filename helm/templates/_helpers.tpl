{{/*
Resolve server configuration values with backwards compatibility.

The top-level values key was renamed from 'zenml' to 'server'. This helper
merges both keys so existing deployments using 'zenml:' continue to work.

Helm always populates .Values.server with the chart defaults from
values.yaml, so we start with those as the base and let user-provided
'zenml:' overrides win via mustMergeOverwrite. We use mustMergeOverwrite
(not merge) because Go's mergo.Merge treats zero-values (false, 0, "")
as empty and silently drops them; mustMergeOverwrite preserves them.

When users adopt the new 'server:' key their overrides are baked into
.Values.server by Helm's own values merge and are already in the base.
*/}}
{{- define "zenml.serverValues" -}}
{{- $server := deepCopy (.Values.server | default dict) -}}
{{- $legacy := deepCopy (.Values.zenml | default dict) -}}
{{- mustMergeOverwrite $server $legacy | toYaml -}}
{{- end -}}

{{/*
Expand the name of the chart.
*/}}
{{- define "zenml.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "zenml.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "zenml.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "zenml.labels" -}}
helm.sh/chart: {{ include "zenml.chart" . }}
{{ include "zenml.selectorLabels" . }}
{{- if .Chart.Version }}
app.kubernetes.io/version: {{ .Chart.Version | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "zenml.selectorLabels" -}}
{{- $server := include "zenml.serverValues" . | fromYaml -}}
app.kubernetes.io/name: {{ include "zenml.name" . }}
{{- if $server.instanceLabel }}
app.kubernetes.io/instance: {{ $server.instanceLabel | quote }}
{{- else }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
{{- end }}

{{/*
Selector labels for server-only resources
*/}}
{{- define "zenml.serverSelectorLabels" -}}
{{ include "zenml.selectorLabels" . }}
app.kubernetes.io/component: server
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "zenml.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "zenml.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Build the complete NO_PROXY list
*/}}
{{- define "zenml.noProxyList" -}}
{{- $server := include "zenml.serverValues" . | fromYaml -}}
{{- $noProxy := $server.proxy.noProxy -}}
{{- /* Add the server URL hostname */ -}}
{{- if $server.serverURL -}}
{{- $serverURL := urlParse $server.serverURL -}}
{{- if not (contains $serverURL.host $noProxy) -}}
{{- $noProxy = printf "%s,%s" $noProxy $serverURL.host -}}
{{- end -}}
{{- end -}}
{{- /* Add the ingress hostname if specified */ -}}
{{- if $server.ingress.host -}}
{{- if not (contains $server.ingress.host $noProxy) -}}
{{- $noProxy = printf "%s,%s" $noProxy $server.ingress.host -}}
{{- end -}}
{{- end -}}
{{- /* Add the gateway hostname if specified */ -}}
{{- if $server.gateway.host -}}
{{- if not (contains $server.gateway.host $noProxy) -}}
{{- $noProxy = printf "%s,%s" $noProxy $server.gateway.host -}}
{{- end -}}
{{- end -}}
{{- range $server.proxy.additionalNoProxy -}}
{{- $noProxy = printf "%s,%s" $noProxy . -}}
{{- end -}}
{{- /* Add service hostnames if they're not already included */ -}}
{{- if not (contains ".svc" $noProxy) -}}
{{- $noProxy = printf "%s,%s" $noProxy (include "zenml.fullname" .) -}}
{{- $noProxy = printf "%s,%s-dashboard" $noProxy (include "zenml.fullname" .) -}}
{{- end -}}
{{- $noProxy -}}
{{- end -}}
