
import base_configuration
from ..core.status import Status

class PowerDeviationMatrixConfiguration(base_configuration.XmlBase):

    def __init__(self, path = None):

        if path != None:

            self.isNew = False
            doc = self.readDoc(path)

            self.path = path

            matrixNode = self.getNode(doc, 'PowerDeviationMatrix')

            self.name = self.getNodeValue(matrixNode, 'Name')
            self.outOfRangeValue = self.getNodeFloat(matrixNode, 'OutOfRangeValue')

            dimensionsNode = self.getNode(matrixNode, 'Dimensions')

            self.dimensions = []

            for node in self.getNodes(dimensionsNode, 'Dimension'):

                parameter = self.getNodeValue(node, 'Parameter')
                centerOfFirstBin = self.getNodeFloat(node, 'CenterOfFirstBin')
                binWidth = self.getNodeFloat(node, 'BinWidth')
                numberOfBins = self.getNodeFloat(node, 'NumberOfBins')

                self.dimensions.append(PowerDeviationMatrixDimension(parameter, centerOfFirstBin, binWidth, numberOfBins))

            if len(self.dimensions) < 1:
                raise Exception("Matrix has zero dimensions")

            cellsNode = self.getNode(doc, 'Cells')

            self.cells = {}

            for cellNode in self.getNodes(cellsNode, 'Cell'):

                cellDimensionsNode = self.getNode(cellNode, 'CellDimensions')

                cellDimensions = {}

                for cellDimensionNode in self.getNodes(cellDimensionsNode, 'CellDimension'):
                    parameter = self.getNodeValue(cellDimensionNode, 'Parameter')
                    center = self.getNodeFloat(cellDimensionNode, 'BinCenter')
                    cellDimensions[parameter] = center

                value = self.getNodeFloat(cellNode, 'Value')

                cellKeyList = []

                for i in range(len(self.dimensions)):
                    dimension = self.dimensions[i]
                    parameter = dimension.parameter
                    binCenter = cellDimensions[parameter]
                    cellKeyList.append(self.getBin(dimension, binCenter))

                key = tuple(cellKeyList)

                self.cells[key] = value

        else:

            self.isNew = True
            self.name = ""
            self.dimensions = []
            self.cells = {}


    def save(self, path, dimensions, matrix):

        self.isNew = False

        doc = self.createDocument()
        root = self.addRootNode(doc, "PowerDeviationMatrix", "http://www.pcwg.org")

        self.addTextNode(doc, root, "Name", self.name)
        self.addFloatNode(doc, root, "OutOfRangeValue", 0.0)

        dimensions_node = self.addNode(doc, root, "Dimensions")

        for dimension in dimensions:

            dimension_node = self.addNode(doc, dimensions_node, "Dimension")

            self.addTextNode(doc, dimension_node, "Parameter", dimension.parameter)
            self.addFloatNode(doc, dimension_node, "CenterOfFirstBin", dimension.bins.centerOfFirstBin)
            self.addFloatNode(doc, dimension_node, "BinWidth", dimension.bins.binWidth)
            self.addIntNode(doc, dimension_node, "NumberOfBins", dimension.bins.numberOfBins)

        cells_node = self.addNode(doc, root, "Cells")

        self.add_cells(doc, cells_node, dimensions, matrix.matrix)
        
        self.path = path        
        self.saveDocument(doc, self.path)

    def add_cells(self, doc, cells_node, dimensions, matrix, centers = None):

        if centers is None:
            dimension_index = 0
        else:
            dimension_index = len(centers)

        dimension = dimensions[dimension_index]

        for i in range(dimension.bins.numberOfBins):

            center = dimension.bins.binCenterByIndex(i)

            if center in matrix:

                value = matrix[center]

                if dimension_index == 0:
                    next_centers = []
                else: 
                    next_centers = list(centers)
                
                next_centers.append(center)

                if len(next_centers) == len(dimensions):
                    self.write_cell(doc, cells_node, dimensions, next_centers, float(value))
                else:
                    self.add_cells(doc, cells_node, dimensions, value, next_centers)

    def write_cell(self, doc, cells_node, dimensions, centers, value):

        cell_node = self.addNode(doc, cells_node, "Cell")

        cell_dimensions_node = self.addNode(doc, cell_node, "CellDimensions")        

        for i in range(len(dimensions)):

            cell_dimension_node = self.addNode(doc, cell_dimensions_node, "CellDimension")        

            self.addTextNode(doc, cell_dimension_node, "Parameter", dimensions[i].parameter)
            self.addFloatNode(doc, cell_dimension_node, "BinCenter", centers[i])

        self.addFloatNode(doc, cell_node, "Value", value)

    def getBin(self, dimension, value):
        return round(round((value - dimension.centerOfFirstBin) / dimension.binWidth, 0) * dimension.binWidth + dimension.centerOfFirstBin, 4)
    
    def __getitem__(self, parameters):

        if len(self.dimensions) < 1:
            raise Exception("Matrix has zero dimensions")

        keyList = []

        for dimension in self.dimensions:
        
            value = parameters[dimension.parameter]
            
            binValue = self.getBin(dimension, value)

            if not dimension.withinRange(binValue):
                return self.outOfRangeValue
            
            keyList.append(binValue)

        key = tuple(keyList)

        if not key in self.cells:

            message = "Matrix value not found:\n"

            for dimension in self.dimensions:
                value = parameters[dimension.parameter]
                message += "%s: %f (%f) - (%f to %f)\n" % (dimension.parameter, value, self.getBin(dimension, value), dimension.centerOfFirstBin, dimension.centerOfLastBin)
            
            Status.add(message)

            raise Exception(message)
        
        return self.cells[key]

class PowerDeviationMatrixDimension(object):

    def __init__(self, parameter='Normalised Hub Wind Speed', index=1, centerOfFirstBin=None, binWidth=None, numberOfBins=None):
        self.calculate_last_bin = False
        self.parameter = parameter
        self.index = index
        self.centerOfFirstBin = centerOfFirstBin
        self.binWidth = binWidth
        self.numberOfBins = numberOfBins
        self.calculate_last_bin = True
        self.calculate_center_of_last_bin()

    @property
    def binWidth(self): 
        return self._binWidth

    @binWidth.setter
    def binWidth(self, value): 
        self._binWidth = value
        self.calculate_center_of_last_bin()

    @property
    def numberOfBins(self): 
        return self._numberOfBins

    @numberOfBins.setter
    def numberOfBins(self, value): 
        self._numberOfBins = value
        self.calculate_center_of_last_bin()

    @property
    def centerOfFirstBin(self): 
        return self._centerOfFirstBin

    @centerOfFirstBin.setter
    def centerOfFirstBin(self, value): 
        self._centerOfFirstBin = value
        self.calculate_center_of_last_bin()

    def calculate_center_of_last_bin(self):

        if self.calculate_last_bin:
            if (self.centerOfFirstBin is None) or (self.binWidth is None) or (self.numberOfBins is None):
                self.centerOfLastBin = None
            else:
                self.centerOfLastBin = self.centerOfFirstBin + self.binWidth * (self.numberOfBins - 1)
        else:
            self.centerOfLastBin = None
            
    def withinRange(self, value):
        if value < self.centerOfFirstBin: return False
        if value > self.centerOfLastBin: return False
        return True

