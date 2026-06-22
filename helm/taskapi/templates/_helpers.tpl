{{- define "taskapi.name" -}}
{{ .Chart.Name }}
{{- end -}}

{{- define "taskapi.labels" -}}
app: {{ include "taskapi.name" . }}
app.kubernetes.io/name: {{ include "taskapi.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
