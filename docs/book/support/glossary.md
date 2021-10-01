# Glossary

**DAG**

Pipelines are traditionally represented as DAGs. DAG is an acronym for Directed Acyclic Graph.

* Directed, because the nodes of the graph \(i.e. the steps of a pipeline\), have a sequence. Nodes do not exist as free-standing entities in this way.
* Acyclic, because there must be one \(or more\) straight paths through the graph from the beginning to the end. It is acyclic because the graph doesn't loop back on itself at any point.
* Graph, because the steps of the pipeline are represented as nodes in a graph.

ZenML follows this paradigm and it is a useful mental model to have in your head when thinking about how the pieces of your pipeline get executed and how dependencies between the different stages are managed.

