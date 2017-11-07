from troposphere import Template, Ref

from troposphereWrapper.codebuild import *
from troposphereWrapper.pipeline import *
from troposphereWrapper.iam import *

from typing import List

def getCodeFromFile(filepath: str) -> List[str]:
  with open (filepath, "r") as xs:
    code = xs.readlines()
  return code


def getBuildRole() -> Role:
  codebuildPolicy = PolicyBuilder() \
      .setName("CodeBuildPolicy") \
      .addStatement(
        StatementBuilder() \
          .setEffect(Effects.Allow) \
          .addAction(awacs.aws.Action("*")) \
          .addResource("*")
          .build() \
          ) \
      .build()
  return RoleBuilder() \
    .setName("LambdaCodeBuildRole") \
    .setAssumePolicy(
      RoleBuilderHelper() \
        .defaultAssumeRolePolicyDocument("codebuild.amazonaws.com")
      ) \
    .addPolicy(codebuildPolicy) \
    .build()




def getBuildSpec(input: str) -> List[str]:
  return getCodeFromFile("codebuild_spec.yaml")


def buildCfWithDockerAction(buildRef, inputName, outputName):
    actionid = CodePipelineActionTypeIdBuilder() \
      .setCodeBuildSource("1") \
      .build()
    return CodePipelineActionBuilder() \
      .setName("BuildCfWithDockerAction") \
      .setActionType(actionid) \
      .addInput(InputArtifacts( Name = inputName )) \
      .addOutput(OutputArtifacts( Name = outputName )) \
      .setConfiguration( { "ProjectName" : Ref(buildRef) } ) \
      .build()


def buildStage(buildRef, inputName: str, outputName: str) -> Stages:
    action = buildCfWithDockerAction( \
                  buildRef, inputName, outputName)
    return CodePipelineStageBuilder() \
      .setName("Build") \
      .addAction(action) \
      .build()


def getCodeBuild(serviceRole: Role, buildspec: List[str]):
  name = "BackEndLambdaBuilder"
  env = CodeBuildEnvBuilder() \
        .setComputeType("BUILD_GENERAL1_SMALL") \
        .setImage("frolvlad/alpine-python3") \
        .setType("LINUX_CONTAINER") \
        .setPrivilegedMode(False) \
        .addEnvVars( { "Name": "APP_NAME", "Value": name } ) \
        .build()
  source = CodeBuildSourceBuilder() \
        .setType(CBSourceType.CodePipeline) \
        .setBuildSpec(Join("", buildspec)) \
        .build()
  artifacts = CodeBuildArtifactsBuilder() \
        .setType(CBArtifactType.CodePipeline) \
        .build()
  return CodeBuildBuilder() \
        .setArtifacts(artifacts) \
        .setEnvironment(env) \
        .setSource(source) \
        .setName(name) \
        .setServiceRole(Ref(serviceRole)) \
        .build()


def getBuild(template: Template, inputName: str, outputName: str) -> Stages:
  role = template.add_resource(getBuildRole())
  spec = getBuildSpec(inputName)
  cb = getCodeBuild(role, spec)
  build_ref = template.add_resource(cb)
  return buildStage(build_ref, inputName, outputName)
