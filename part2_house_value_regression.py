import torch
import pickle
import numpy as np
import pandas as pd
from sklearn import preprocessing, model_selection #For one-hot encoding and GridSearch for hyperparam tuning
import collections
import math
import random
import torch.nn as nn

class Regressor():
    def __init__(self, paramDict=None):
        # You can add any input parameters you need
        # Remember to set them with a default value for LabTS tests
        """ 
        Initialise the model.
          
        Arguments:
            - x {pd.DataFrame} -- Raw input data of shape 
                (batch_size, input_size), used to compute the size P
                of the network.
            - nb_epoch {int} -- number of epochs to train the network.

        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        #Hyperparameter setting
        self.minImprovement = 0.1
        if paramDict is None:
            #Default values
            paramDict = {
            "nb_epoch" : 500, 
            "learningRate" : 0.1,
            "neuronArchitecture" : [13, 9], 
            "batchSize" : 128
            }
        # self.paramDict = paramDict
        # self.nb_epoch = paramDict["nb_epoch"]
        # self.learningRate = paramDict["learningRate"]
        # self.neuronArchitecture = paramDict["neuronArchitecture"]
        # self.batchSize = paramDict["batchSize"]
        self.nb_epoch = 500
        self.learningRate = 0.01
        self.neuronArchitecture = [13,9]
        self.batchSize = 32
        #Ensure first layer contains 13 neurons to match input feature size
        self.neuronArchitecture = [13] + self.neuronArchitecture 
        #Convert string labels to numerical
        self.bin_labels  = preprocessing.LabelBinarizer()
        self.bin_labels.classes = ["<1H OCEAN","INLAND","NEAR OCEAN","NEAR BAY","NEAR OCEAN"]
        #Neuron architecture
        self.output_layer = nn.Linear(in_features=self.neuronArchitecture[-1],out_features=1)
        self.layer_list = []
        for i in range(len(self.neuronArchitecture)-1): #list of input and all hidden layers
            self.layer_list.append(nn.Linear(in_features=self.neuronArchitecture[i],out_features=self.neuronArchitecture[i+1]))
            self.layer_list.append(nn.ReLU())
        self.layer_list.append(self.output_layer)
        self.model = nn.Sequential(*self.layer_list) #unpacks list as parameters for sequential layers
        self.model.apply(self.init_weights)
        self.model.to(torch.float64)
        #Loss function
        self.loss = nn.MSELoss()
        return
        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################
    def _preprocessor(self, x, y = None, training = False):

        """ 
        Preprocess input of the network.
          
        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
            - y {pd.DataFrame} -- Raw target array of shape (batch_size, 1).
            - training {boolean} -- Boolean indicating if we are training or 
                testing the model.

        Returns:
            - {torch.tensor} or {numpy.ndarray} -- Preprocessed input array of
              size (batch_size, input_size). The input_size does not have to be the same as the input_size for x above.
            - {torch.tensor} or {numpy.ndarray} -- Preprocessed target array of
              size (batch_size, 1).
            
        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        
        #Fills empty data points with averages of their column
        pd.options.mode.chained_assignment = None
        for col in x:
            if col in {"longitude","latitude", "median_income"}:
                x[col].fillna(x[col].mean(), inplace=True)
            elif col == "ocean_proximity":
                x[col].fillna(x[col].mode()[0], inplace=True)
            else:
                x[col].fillna(x[col].median(), inplace=True)
        proximity_column  = pd.DataFrame(self.bin_labels.fit_transform(x["ocean_proximity"]))
        x = x.drop(columns="ocean_proximity",axis = 1)
        x = x.join(proximity_column)
        if training:
            #Determine scaling factors
            self.xMin = x.min()
            self.xMax = x.max()
            self.xRange = self.xMax-self.xMin
        #Normalises numerical data from a scale of 0-1
        x = (x-self.xMin)/(self.xMax-self.xMin)
        #converts x and y to tensors before returning
        return torch.from_numpy(x.values), (torch.from_numpy(y.values) if isinstance(y, pd.DataFrame) else None)
        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################
    def fit(self, x, y, xValidation=None, yValidation=None, minImprovement=0.03):
        """
        Regressor training function

        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
            - y {pd.DataFrame} -- Raw output array of shape (batch_size, 1).

        Returns:
            self {Regressor} -- Trained model.

        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        #Preprocess training data to generate scalars
        X, Y = self._preprocessor(x, y = y, training = True)
        #Mini-batch gradient descent:
        torch.set_printoptions(profile="full")
        currEpoc = 0
        epochError = math.inf
        while currEpoc < self.nb_epoch:
            batch_list = torch.randperm(len(X)) # generates random indices
            for i in range(0,len(X),self.batchSize):
                #print("batch number:", i//self.batchSize, "of", len(X)//self.batchSize, end=" ")
                network = torch.optim.Adam(self.model.parameters(), lr=self.learningRate)
                network.zero_grad()
                index = batch_list[i:i+self.batchSize]
                batch_x = X[index]
                batch_y = Y[index]
                prediction = self.predict(batch_x)
                batch_loss = self.loss(prediction,batch_y)#wrapper function
                #print(f"Pred: {(int(prediction[3]))} actual: {int(batch_y[3])}, factor: {float(prediction[3]/batch_y[3])}", end = ' ')
                # rmse = prediction-batch_y
                # total = 0
                # for element in rmse:
                #     total += element**2
                # total = math.sqrt(total/len(prediction))
                # print("RMSE:", total)
                #print(f"Pred: {(batch_y-prediction)}")# actual: {batch_y}")
                batch_loss.backward()
                network.step()
            currEpoc += 1
            #Use the validation set to implement early stopping - used during hyperparamter tuning
            # if xValidation is not None:
            #     newError = self.score(x, y)
            #     if 1-(newError/epochError) < minImprovement:
            #         print("Reached epoch cycle:", currEpoc, "with error:", newError)
            #         break
            #     epochError = newError
        #print(self.score(X, Y, False))
        return
        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################

            
    def predict(self, x):
        """
        Output the value corresponding to an input x.

        Arguments:
            x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
        
        Returns:
            {np.ndarray} -- Predicted value for the given input (batch_size, 1).

        """
        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        return self.model(x)
        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################

    def score(self, x, y):
        """
        Function to evaluate the model accuracy on a validation dataset.

        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
            - y {pd.DataFrame} -- Raw output array of shape (batch_size, 1).

        Returns:
            {float} -- Quantification of the efficiency of the model.

        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        X, Y = self._preprocessor(x, y)
        yPred = self.predict(X)
        diff = yPred-Y
        #Calculate RMSE
        total = 0
        for element in diff:
            total += element**2
        return math.sqrt(total/len(diff))
        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################

    # All helper functions in class
    @staticmethod
    def init_weights(layer):
        if isinstance(layer, nn.Linear):
            nn.init.xavier_uniform_(layer.weight)
            layer.bias.data.fill_(0)
    
    def earlyStop(self, validationLoss, minImprovement):
        pass

    def get_params(self):
        return self.paramDict
    
def save_regressor(trained_model): 
    """ 
    Utility function to save the trained regressor model in part2_model.pickle.
    """
    # If you alter this, make sure it works in tandem with load_regressor
    with open('part2_model.pickle', 'wb') as target:
        pickle.dump(trained_model, target)
    print("\nSaved model in part2_model.pickle\n")


def load_regressor(): 
    """ 
    Utility function to load the trained regressor model in part2_model.pickle.
    """
    # If you alter this, make sure it works in tandem with save_regressor
    with open('part2_model.pickle', 'rb') as target:
        trained_model = pickle.load(target)
    print("\nLoaded model in part2_model.pickle\n")
    return trained_model

# Helper functions
#This function will find the top two paramters and create a range between them
def getTopTwo(inputList):
    paramHeaders = {"learningRate" : 0, "neuronArchitecture" : 1, "batchSize" : 2}
    params = [[] for i in range(len(paramHeaders))]
    paramMode = dict()
    #Convert list of dictionaries to list per parameter
    for description in inputList:
        for key, value in description.items():
            params[paramHeaders[key]].append(value)
    #Invert the dictionary
    paramInverted = {value: key for key, value in paramHeaders.items()}
    #Obtain the two most common items
    for index, value in enumerate(params):
        mode = collections.Counter(params[index]).most_common(2)
        paramMode[paramInverted[index]] = [i[0] for i in mode]
    return paramMode

def RegressorHyperParameterSearch(x, y, hyperparam, minImprovement=0.1, candidateThreshold=0.05, iterations=3, wideSearch=True): 
    # Ensure to add whatever inputs you deem necessary to this function
    """
    Performs a hyper-parameter for fine-tuning the regressor implemented 
    in the Regressor class.
    The approach is to start with very wide hyperparameters, and iteratively modify the hyperparamters for the next iteration
    based on the top 'candidateThreshold' % of models in the current iteration.
    The primary goal of the first iteration is to determine how many layers of neurons should be used and the order of magntiude for the learning rate
    Arguments:
        Add whatever inputs you need.
        
    Returns:
        The function should return your optimised hyper-parameters. 

    """
    #######################################################################
    #                       ** START OF YOUR CODE **
    #######################################################################
    iteration = 0
    bestPerformer = 0
    bestParams = None
    while iteration < iterations:
        xTrain, xValidation, yTrain, yValidation = model_selection.train_test_split(x, y, test_size=0.1, shuffle=True)
        iteration += 1
        model = model_selection.GridSearchCV(
            estimator = Regressor(x),
            param_grid = hyperparam,
            scoring="neg_root_mean_squared_error", #Scoring metric means lower is better
            cv=5,
            verbose=2,
            n_jobs=-1,
            return_train_score = True
            )
        model.fit(xTrain, yTrain, xValidation=xValidation, yvValidation=yValidation, minImprovement=minImprovement)
        results = pd.DataFrame(model.cv_results_) #Get results
        currentPerformer = results["mean_test_score"].max() #Find best performer from models
        #If the newest iteration has a worse performance, terminate tuning and return the last one
        if bestPerformer > currentPerformer:
            return bestParams
        bestPerformer = currentPerformer
        bestParams = model.best_params_dict
        #Get all models within 'candidateThreshold' % of best performance
        results = results.loc[results["mean_test_score"] >= bestPerformer-candidateThreshold]
        paramList = results["params"]
        #Now, calculate all the new hyperparameters and prepare for next round
        print("Iteration", iteration)
        print("Found params:", paramList)
        newParams = getTopTwo(paramList)
        print("Optimum params:", newParams)
        #On the first iteration, determine magnitude of learning rate and the amount of layers in the neural network
        if iteration == 1:
            #Determine the amount of layers - prefer less layers
            layerCount = [len(x) for x in newParams["neuronArchitecture"]].min()
            #Determine the magnitude of the learning rate 
            if wideSearch and len(newParams["learningRate"][0]) >= 2:
                learningMagnitude = [math.log(x, 10) for x in newParams["learningRate"][:2]].sum()/2
            else:
                learningMagnitude = math.log(newParams["learningRate"][0], 10)
            print("Layercount:", layerCount, "Learning Magnitude:", learningMagnitude)
        hyperparam = {"learningRate" : None, "neuronArchitecture" : [], "batchSize" : None}
        hyperparam["learningRate"] = [10**random.uniform(learningMagnitude-0.3, learningMagnitude+0.3) for _ in range(4)]
        #Neuron architecture
        for i in range(4):
            maxNeurons = 13
            architecture = []
            for j in range(layerCount):
                #Ensure decreasing neurons
                maxNeurons = random.randint(maxNeurons-3, maxNeurons)
                architecture.append(maxNeurons)
            hyperparam["neuronArchitecture"].append(architecture)
        #Batchsize
        if len(newParams["batchSize"][0]) >= 2:
            batchMagnitude = [math.log(x, 2) for x in newParams["batchSize"][:2]].sum()/2
        else:
            batchMagnitude = math.log(newParams["batchSize"][0], 2)
        hyperparam["batchSize"] = [2**random.uniform(batchMagnitude-0.3, batchMagnitude+0.3) for _ in range(4)]
        print("New hyperparameters:", hyperparam)
    return bestParams # Return the chosen hyper parameters
    #######################################################################
    #                       ** END OF YOUR CODE **
    #######################################################################
    #https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html
    #https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html




def example_main():

    output_label = "median_house_value"

    # Use pandas to read CSV data as it contains various object types
    # Feel free to use another CSV reader tool
    # But remember that LabTS tests take Pandas DataFrame as inputs
    data = pd.read_csv("housing.csv") 

    # Splitting input and output
    x_train = data.loc[:, data.columns != output_label]
    y_train = data.loc[:, [output_label]]
    #Hyperparameter tuning
    hyperparam = {
        "nb_epoch" : 1000, 
        "learningRate" : [0.001, 0.01, 0.1, 1], 
        "neuronArchitecture" : [[9], [9,9], [9,9,9], [9,9,9,9]], 
        "batchSize" : [64, 128, 256, 512],
        }
    #bestParams = RegressorHyperParameterSearch(x_train, y_train, hyperparam, minImprovement=0.01, candidateThreshold=0.05, iterations=3)
    #print("Optimum parameters:", bestParams)
    # Training
    # This example trains on the whole available dataset. 
    # You probably want to separate some held-out data 
    # to make sure the model isn't overfitting
    regressor = Regressor()
    regressor.fit(x_train, y_train)
    #regressor.score(x, y) #need this to compare against parameter tuning maybe make held out dataset?
    save_regressor(regressor)

    # Error
    error = regressor.score(x_train, y_train)
    print("\nRegressor error: {}\n".format(error))


        

if __name__ == "__main__":
    example_main()

## Sources: https://machinelearningmastery.com/difference-between-a-batch-and-an-epoch/
##          https://pandas.pydata.org/
##          https://pytorch.org/docs/
##          https://www.projectpro.io/recipes/optimize-function-adam-pytorch
##          https://stackoverflow.com/questions/32896651/pass-multiple-arguments-in-form-of-tuple
##          https://rubikscode.net/2021/08/02/pytorch-for-beginners-building-neural-networks/
##          https://scikit-learn.org/stable/developers/develop.html