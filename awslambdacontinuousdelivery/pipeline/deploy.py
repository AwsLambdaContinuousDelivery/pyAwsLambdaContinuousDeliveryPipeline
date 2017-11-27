from troposphere import Template, GetAtt, Ref, Sub

from awacs.ec2 import *
from awacs.iam import *
from awacs.awslambda import *
from troposphere.iam import Role
from troposphereWrapper.pipeline import *
from troposphereWrapper.iam import *
from tests import *

from typing import Tuple
import re

regex = re.compile('[^a-zA-Z0-9]')

def getDeployResources(t: Template, stack: str) -> Tuple[ActionTypeID, Role]:
  policyDoc = PolicyDocumentBuilder() \
    .addStatement(StatementBuilder() \
        .addAction(awacs.ec2.Action("*")) \
        .addAction(awacs.awslambda.GetFunction) \
        .addAction(awacs.awslambda.CreateFunction) \
        .addAction(awacs.awslambda.GetFunctionConfiguration) \
        .addAction(awacs.awslambda.DeleteFunction) \
        .addAction(awacs.awslambda.UpdateFunctionCode) \
        .addAction(awacs.awslambda.UpdateFunctionConfiguration) \
        .addAction(awacs.awslambda.CreateAlias) \
        .addAction(awacs.awslambda.DeleteAlias) \
        .setEffect(Effects.Allow) \
        .addResource("*") \
        .build() 
      ) \
    .addStatement(StatementBuilder() \
        .addAction(awacs.iam.DeleteRole) \
        .addAction(awacs.iam.DeleteRolePolicy) \
        .addAction(awacs.iam.GetRole) \
        .addAction(awacs.iam.PutRolePolicy) \
        .addAction(awacs.iam.CreateRole) \
        .addAction(awacs.iam.PassRole)
        .setEffect(Effects.Allow) \
        .addResource("*") \
        .build()
      ) \
    .build()

  policy = Policy( PolicyDocument = policyDoc
                 , PolicyName = "CloudFormationDeployPolicy"
                 )

  role = t.add_resource( RoleBuilder() \
          .setName(regex.sub('', "CFDeplyRole" + stack)) \
          .setAssumePolicy(RoleBuilderHelper() \
            .defaultAssumeRolePolicyDocument("cloudformation.amazonaws.com")) \
          .addPolicy(policy) \
          .build()
         )

  actionId = CodePipelineActionTypeIdBuilder() \
      .setCategory(ActionIdCategory.Deploy) \
      .setOwner(ActionIdOwner.AWS) \
      .setProvider("CloudFormation") \
      .setVersion("1") \
      .build()
  return [actionId, role]


def getDeploy( t: Template
             , inName: str
             , stage: str
             , stack: str
             , resource: Tuple[ActionTypeID, Role]
             , code: str = None) -> Stages:
  [actionId, role] = resource
  config = { "ActionMode" : "CREATE_UPDATE"
           , "RoleArn" : GetAtt(role, "Arn")
           , "StackName" : Sub("".join([stack,"${AWS::StackName}", stage]))
           , "Capabilities": "CAPABILITY_NAMED_IAM"
           , "TemplatePath" : inName + "::stack" + stage + ".json"
           }
  action = CodePipelineActionBuilder() \
      .setName("Deploy" + stack + stage) \
      .setActionType(actionId) \
      .addInput(InputArtifacts(Name = inName)) \
      .addOutput(OutputArtifacts(Name = stage)) \
      .setConfiguration(config) \
      .build()
  
  s = CodePipelineStageBuilder() \
      .setName(stage + "_Deploy") \
      .addAction(action)
  if code is not None:
    s.addAction(getTest(t, code, stack, stage))
  return s.build()