# How to Write an Integration Example

## 🥅 Our Goals for the examples

- First touchpoint for the user with the integration
- Location for copy-pasting integration specific code
- Integration Test
- Place for us to play around during development of addtl. features

##  📝 Write the Example

![KISS](assets/KISS.png)

In keeping with the goal of examples, remember to keep it simple. Avoid unnecessary dependencies, unnecessary 
configuration parameters and unnecessary code complexity in general.

### 🖼 This is what a minimal example could look like

This is example stays as simple as possible, while showing how to create a custom materializer. We have a minimal Object
to materialize, we have a minimal pipeline that shows a step that produces this object and a step that consumes the 
object.

  ```python
  class MyObj:
      def __init__(self, name: str):
          self.name = name
  
  class MyMaterializer(BaseMaterializer):
      ASSOCIATED_TYPES = (MyObj,)
      ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)
  
      def handle_input(self, data_type: Type[MyObj]) -> MyObj:
          """Read from artifact store"""
          super().handle_input(data_type)
          with fileio.open(os.path.join(self.artifact.uri, "data.txt"), "r") as f:
              name = f.read()
          return MyObj(name=name)
  
      def handle_return(self, my_obj: MyObj) -> None:
          """Write to artifact store"""
          super().handle_return(my_obj)
          with fileio.open(os.path.join(self.artifact.uri, "data.txt"), "w") as f:
              f.write(my_obj.name)
  
  @step
  def step1() -> MyObj:
      return MyObj("jk")
  
  @step
  def step2(my_obj: MyObj):
      print(my_obj.name)
  
  @pipeline
  def pipe(step1, step2):
      step2(step1())
  
  if __name__ == "__main__":
      pipe(
          step1=step1().with_return_materializers(MyMaterializer), step2=step2()
      ).run()
  ```

## 📰 Write the Readme

[Here](template_README.md) is a template, make sure to replace everything in square brackets. Depending on your specific
example feel free to add or remove sections where applicable.

## ⚙️ Create setup.sh

The setup.sh file is necessary to support example run cli command. Within the setup.sh file you'll need to define what 
ZenML integrations need to be installed. Find the template [here](template_setup.sh).

In case your example has requirements that are not ZenML integrations you can also add a requirements.txt file with
those packages.

## 🧪 Test ZenML Example CLI

Our example cli commands serve as a super quick entrypoint for users. As such it is important to make sure your new example can be executed 
with the following command: 

```shell
zenml example pull
zenml example run [EXAMPLE NAME]
```

This will pull examples from the latest release, copy them to your current working directory and run it using the
[run_example.sh](../run_example.sh).

In order to test your local example you'll need to make sure that your local code is used instead of the
latest release version. To do this you need to run the following commands:

# TODO: IMPLEMENT THIS

## ➕ Add to main REAMDE file

In the [main README](../README.md), make sure to add your example to the correct cluster or create a new cluster with a
description if your integration does not fit the preexisting ones.
