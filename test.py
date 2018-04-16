#encoding:utf8
#Author：lvpengbin
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
from sklearn.datasets import load_iris
from sklearn import tree
from sklearn.externals.six import StringIO
import pydot
import pydotplus 

iris = load_iris()#载入数据集
clf = tree.DecisionTreeClassifier()#算法模型
clf = clf.fit(iris.data, iris.target)#模型训练
dot_data = tree.export_graphviz(clf, out_file=None)
graph = pydotplus.graph_from_dot_data(dot_data) 
graph.write_pdf("iris.pdf") 

