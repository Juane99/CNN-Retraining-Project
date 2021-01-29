# -*- coding: utf-8 -*-
"""Proyecto_Final_VC.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HX6sHlpB8B2-L9l1K7oTczfeULVY2-9v
"""

# EJECUTAR PARA COLAB: EfficientNet todavia no está en la version de tensorflow
# normal, está en la nightly
# !pip install tf-nightly

#Librerias y Funciones


#########################################################################
################ CARGAR LAS LIBRERÍAS NECESARIAS ########################
#########################################################################

# Terminar de rellenar este bloque con lo que vaya haciendo falta

# Importar librerías necesarias
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import keras
import keras.utils as np_utils
from keras.preprocessing.image import load_img,img_to_array
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# Importar el optimizador a usar
from keras.optimizers import Adam

# Importar modelos y capas específicas que se van a usar
from keras.models import Sequential
from keras import Model
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, BatchNormalization

#Importamos el ImageDataGenerator
from keras.preprocessing.image import ImageDataGenerator

# Importar el modelo ResNet50 y su respectiva función de preprocesamiento,
# que es necesario pasarle a las imágenes para usar este modelo
from keras.applications.resnet import ResNet50
from keras.applications.inception_v3 import InceptionV3
from keras.applications.densenet import DenseNet121
from tensorflow.python.keras.applications.efficientnet import EfficientNetB0


from keras.applications.resnet import preprocess_input as preprocesado_resnet
from keras.applications.inception_v3 import preprocess_input as preprocesado_inception
from keras.applications.densenet import preprocess_input as preprocesado_densenet
from tensorflow.python.keras.applications.efficientnet import preprocess_input as preprocesado_efficientnet

from tensorflow.math import confusion_matrix, argmax


#Importamos el Early-Stopping
from keras.callbacks import EarlyStopping

#Para usar Cross-Validation
from sklearn.model_selection import KFold


NUM_CLASES = 9

#########################################################################
################## FUNCIÓN PARA LEER LAS IMÁGENES #######################
#########################################################################

# Dado un fichero train.txt o test.txt y el path donde se encuentran los
# ficheros y las imágenes, esta función lee las imágenes
# especificadas en ese fichero y devuelve las imágenes en un vector y
# sus clases en otro.

def leerImagenes(vec_imagenes, path):
  clases = np.array([img.split('/')[0] for img in vec_imagenes])
  imagenes = np.array([img_to_array(load_img(path + "/" + img,
                                             target_size = (224, 224)))
                       for img in vec_imagenes])

  return imagenes, clases

#########################################################################
############# FUNCIÓN PARA CARGAR EL CONJUNTO DE DATOS ##################
#########################################################################

# Usando la función anterior, y dado el path donde se encuentran las
# imágenes y los archivos "train.txt" y "test.txt", devuelve las
# imágenes y las clases de train y test para usarlas con keras
# directamente.

def cargarDatos(path):
  # Cargamos el fichero con el nombre de las imagenes y las
  #dividimos en train y test usando sklearn

  imagenes_str = np.loadtxt(path + "/files.txt", dtype = str)
  X,y = leerImagenes(imagenes_str,path)

  train, test, train_clases, test_clases = train_test_split(X, y, test_size = 0.20, random_state=25)

  print("leidas")
  # Pasamos los vectores de las clases a matrices
  # Para ello, primero pasamos las clases a números enteros
  clases_posibles = np.unique(np.copy(train_clases))
  for i in range(len(clases_posibles)):
    train_clases[train_clases == clases_posibles[i]] = i
    test_clases[test_clases == clases_posibles[i]] = i

  # Después, usamos la función to_categorical()
  train_clases = np_utils.to_categorical(train_clases, NUM_CLASES)
  test_clases = np_utils.to_categorical(test_clases, NUM_CLASES)

  # Barajar los datos
  train_perm = np.random.permutation(len(train))
  train = train[train_perm]
  train_clases = train_clases[train_perm]

  test_perm = np.random.permutation(len(test))
  test = test[test_perm]
  test_clases = test_clases[test_perm]

  return train, train_clases, test, test_clases

#########################################################################
######## FUNCIÓN PARA OBTENER EL ACCURACY DEL CONJUNTO DE TEST ##########
#########################################################################

# Esta función devuelve el accuracy de un modelo, definido como el
# porcentaje de etiquetas bien predichas frente al total de etiquetas.
# Como parámetros es necesario pasarle el vector de etiquetas verdaderas
# y el vector de etiquetas predichas, en el formato de keras (matrices
# donde cada etiqueta ocupa una fila, con un 1 en la posición de la clase
# a la que pertenece y 0 en las demás).

def calcularAccuracy(labels, preds):
  labels = np.argmax(labels, axis = 1)
  preds = np.argmax(preds, axis = 1)

  accuracy = sum(labels == preds)/len(labels)

  return accuracy

#########################################################################
## FUNCIÓN PARA PINTAR LA PÉRDIDA Y EL ACCURACY EN TRAIN Y VALIDACIÓN ###
#########################################################################

# Esta función pinta dos gráficas, una con la evolución de la función
# de pérdida en el conjunto de train y en el de validación, y otra
# con la evolución del accuracy en el conjunto de train y en el de
# validación. Es necesario pasarle como parámetro el historial
# del entrenamiento del modelo (lo que devuelven las funciones
# fit() y fit_generator()).

def mostrarEvolucion(hist):

  loss = hist.history['loss']
  val_loss = hist.history['val_loss']
  plt.plot(loss)
  plt.plot(val_loss)
  plt.legend(['Training loss', 'Validation loss'])
  plt.show()

  acc = hist.history['accuracy']
  val_acc = hist.history['val_accuracy']
  plt.plot(acc)
  plt.plot(val_acc)
  plt.legend(['Training accuracy', 'Validation accuracy'])
  plt.show()

#########################################################################
##            FUNCIÓN QUE CREA UN MODELO CAMBIANDO SOLO LA ULTIMA CAPA  #
#########################################################################

def soloUltimaCapa(preentrenado):
  x = preentrenado.output
  last = Dense (NUM_CLASES, activation = 'softmax')(x)
  solo_salida = Model(inputs = preentrenado.input, outputs = last)

  opt = Adam(learning_rate=0.001,beta_1=0.9,beta_2=0.999,epsilon=1e-07)

  solo_salida.compile(loss=keras.losses.categorical_crossentropy,optimizer=opt,
                  metrics=['accuracy'])

  return solo_salida


#########################################################################
##            FUNCIÓN QUE CREA UN MODELO AÑADIENDO CAPAS               ##
#########################################################################

def nuevasCapas(preentrenado):
  x = preentrenado.output
  x = Dense(1000,activation="relu")(x)
  x = BatchNormalization(renorm=True)(x)
  x = Dropout(0.5)(x)
  last = Dense (NUM_CLASES, activation = 'softmax')(x)
  salida = Model(inputs = preentrenado.input, outputs = last)

  opt = Adam(learning_rate=0.001,beta_1=0.9,beta_2=0.999,epsilon=1e-07)

  salida.compile(loss=keras.losses.categorical_crossentropy,optimizer=opt,
                  metrics=['accuracy'])

  return salida


#########################################################################
##               FUNCIÓN QUE EJECUTA UN MODELO CONCRETO               ###
#########################################################################


def ejecutaModelo(preentren,x_tra,y_tra,modelo,batch,epoc, funcion_preprocesado):

  #Llamamos a la funcion que crea el modelo con los hiperparámetros anteriormente
  #estimados

  if modelo == 0:
    mod = soloUltimaCapa(preentren)
  elif modelo == 1:
    mod = nuevasCapas(preentren)
  else:
    mod = preentren

  # Definir un objeto de la clase ImageDataGenerator para train y otro para test
  # con sus respectivos argumentos.
  # parametrizada funcion de preprocesado, dependiendo de si se usa ResNet, Inception
  train_datagen = ImageDataGenerator(validation_split=0.1,preprocessing_function = funcion_preprocesado)

  train_generator = train_datagen.flow(x_tra,y_tra,batch_size=batch,subset='training')
  val_generator = train_datagen.flow(x_tra,y_tra, batch_size=batch,subset='validation')

  callback = EarlyStopping(patience=5,restore_best_weights=True)

  historial = mod.fit_generator(train_generator,
                                steps_per_epoch=len(x_tra)*0.9/batch,epochs=epoc,
                                validation_data=val_generator,
                                validation_steps=len(x_tra)*0.1/batch,
                                callbacks=callback)

  #Mostramos la evolucion
  mostrarEvolucion(historial)

  return mod


def matriz_confusion(y_test ,y_predecida):
  # le hacemos el argmax para desaher el to categorical
  matriz_conf = confusion_matrix(labels=argmax(y_test, axis=1), predictions=argmax(y_predecida, axis=1)).numpy()
  matriz_normalizada = np.around(matriz_conf.astype('float') / matriz_conf.sum(axis=1)[:, np.newaxis], decimals=2)

  clases = [i for i in range(NUM_CLASES)]
  dataframe_matriz = pd.DataFrame(matriz_normalizada,
                                  index = clases,
                                  columns = clases)

  figure = plt.figure(figsize=(8, 8))
  sns.heatmap(dataframe_matriz, annot=True,cmap=plt.cm.Blues)
  plt.tight_layout()
  plt.ylabel('Valor real')
  plt.xlabel('Valor predecido')
  plt.show()


# descargamos el conjunto de datos modificado con las clases a usar y el fichero files.txt,
# lo descargamos del drive del que tenemos subido el zip, porque va mucho más rápido
# que leyendolo de drive en colab
# https://drive.google.com/file/d/1gCsMT1B-M9nwYlyJQQu9snykffo3ZUss/view?usp=sharing


#!wget wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1gCsMT1B-M9nwYlyJQQu9snykffo3ZUss' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1gCsMT1B-M9nwYlyJQQu9snykffo3ZUss" -O Images.zip && rm -rf /tmp/cookies.txt

#!ls

# descomprimimos el zip descargado
#!unzip Images.zip

#Cargamos las imagenes para que las pueda leer Keras

x_train,y_train,x_test,y_test = cargarDatos("Images")

#  celda para el codigo de resnet50, por defecto sin include_top para añadir la capa Dense con nuestro numero de clases y pesos de imagenet
red_resnet = ResNet50(include_top = False, pooling = "avg")
red_resnet.trainable = False
red_resnet = ejecutaModelo(red_resnet, x_train, y_train, 0, 64, 20, preprocesado_resnet)
test_datagen_resnet = ImageDataGenerator(preprocessing_function = preprocesado_resnet)
predicciones_resnet = red_resnet.predict_generator(test_datagen_resnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_resnet)
print("Accuracy con ResNet50 entrenando solo ultima capa: {}".format(accuracy))

matriz_confusion(y_test, predicciones_resnet)

# fine tuning de resnet 50
red_resnet.trainable = True
red_resnet = ejecutaModelo(red_resnet, x_train, y_train, -1, 64, 20, preprocesado_resnet)

test_datagen_resnet = ImageDataGenerator(preprocessing_function = preprocesado_resnet)
predicciones_resnet = red_resnet.predict_generator(test_datagen_resnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_resnet)
print("Accuracy con ResNet50 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_resnet)

#  celda para el codigo de EfficientNetB0, por defecto  sin include_top para añadir la capa Dense con nuestro numero de clases y pesos de imagenet
red_efficientnet_b0 = EfficientNetB0(include_top = False, pooling = "avg")
red_efficientnet_b0.trainable = False
red_efficientnet_b0 = ejecutaModelo(red_efficientnet_b0, x_train, y_train, 0, 64, 20, preprocesado_efficientnet)
test_datagen_efficientnet = ImageDataGenerator(preprocessing_function = preprocesado_efficientnet)
predicciones_efficientnet = red_efficientnet_b0.predict_generator(test_datagen_efficientnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_efficientnet)
print("Accuracy con EfficientNetB0 entrenando solo ultima capa: {}".format(accuracy))


matriz_confusion(y_test, predicciones_efficientnet)

# fine tuning de EfficientNet
red_efficientnet_b0.trainable = True
red_efficientnet_b0 = ejecutaModelo(red_efficientnet_b0, x_train, y_train, -1, 64, 20, preprocesado_efficientnet)

test_datagen_efficientnet = ImageDataGenerator(preprocessing_function = preprocesado_efficientnet)
predicciones_efficientnet = red_efficientnet_b0.predict_generator(test_datagen_efficientnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_efficientnet)
print("Accuracy con EfficientNetB0 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_efficientnet)

#  celda para el codigo de DenseNet121, por defecto  sin include_top para añadir la capa Dense con nuestro numero de clases y pesos de imagenet
red_densenet = DenseNet121(include_top = False, pooling = "avg")
red_densenet.trainable = False
red_densenet = ejecutaModelo(red_densenet, x_train, y_train, 0, 64, 20, preprocesado_densenet)
test_datagen_densenet = ImageDataGenerator(preprocessing_function = preprocesado_densenet)
predicciones_densenet = red_densenet.predict_generator(test_datagen_densenet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_densenet)
print("Accuracy con DenseNet121 entrenando solo ultima capa: {}".format(accuracy))


matriz_confusion(y_test, predicciones_densenet)

# fine tuning de Densenet
red_densenet.trainable = True
red_densenet = ejecutaModelo(red_densenet, x_train, y_train, -1, 64, 20, preprocesado_densenet)

test_datagen_densenet = ImageDataGenerator(preprocessing_function = preprocesado_densenet)
predicciones_densenet = red_densenet.predict_generator(test_datagen_densenet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_densenet)
print("Accuracy con DenseNet121 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_densenet)

#  celda para el codigo de Inceptionv3, por defecto  sin include_top para añadir la capa Dense con nuestro numero de clases y pesos de imagenet
red_inception = InceptionV3(include_top = False, pooling = "avg")
red_inception.trainable = False
red_inception = ejecutaModelo(red_inception, x_train, y_train, 0, 64, 20, preprocesado_inception)
test_datagen_inception = ImageDataGenerator(preprocessing_function = preprocesado_inception)
predicciones_inception = red_inception.predict_generator(test_datagen_inception.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_inception)
print("Accuracy con InceptionV3 entrenando solo ultima capa: {}".format(accuracy))


matriz_confusion(y_test, predicciones_inception)

# fine tuning de InceptionV3
red_inception.trainable = True
red_inception = ejecutaModelo(red_inception, x_train, y_train, -1, 64, 20, preprocesado_inception)

test_datagen_inception = ImageDataGenerator(preprocessing_function = preprocesado_inception)
predicciones_inception = red_inception.predict_generator(test_datagen_inception.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_inception)
print("Accuracy con InceptionV3 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_inception)

"""Probamos lo mismo, pero descongelando las últimas 5 capas """

#  celda para el codigo de resnet50, por defecto sin include_top para añadir la capa Dense con nuestro numero de clases y pesos de imagenet
red_resnet = ResNet50(include_top = False, pooling = "avg")
red_resnet.trainable = False
# ponemos los ultimos cinco como entrenables, el resto los fijamos
for layer in red_resnet.layers[-5:]:
  layer.trainable = True
red_resnet = ejecutaModelo(red_resnet, x_train, y_train, 1, 64, 20, preprocesado_resnet)
test_datagen_resnet = ImageDataGenerator(preprocessing_function = preprocesado_resnet)
predicciones_resnet = red_resnet.predict_generator(test_datagen_resnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_resnet)
print("Accuracy con ResNet50 entrenando las ultimas 5 capas: {}".format(accuracy))

matriz_confusion(y_test, predicciones_resnet)

# fine tuning de resnet 50 pero con las últimas 5 capas ya reentrenadas
red_resnet.trainable = True
red_resnet = ejecutaModelo(red_resnet, x_train, y_train, -1, 64, 20, preprocesado_resnet)

test_datagen_resnet = ImageDataGenerator(preprocessing_function = preprocesado_resnet)
predicciones_resnet = red_resnet.predict_generator(test_datagen_resnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_resnet)
print("Accuracy con ResNet50 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_resnet)

red_efficientnet_b0 = EfficientNetB0(include_top = False, pooling = "avg")
red_efficientnet_b0.trainable = False
# ponemos los ultimos cinco como entrenables, el resto los fijamos
for layer in red_efficientnet_b0.layers[-5:]:
  layer.trainable = True
red_efficientnet_b0 = ejecutaModelo(red_efficientnet_b0, x_train, y_train, 1, 64, 20, preprocesado_efficientnet)
test_datagen_efficientnet = ImageDataGenerator(preprocessing_function = preprocesado_efficientnet)
predicciones_efficientnet = red_efficientnet_b0.predict_generator(test_datagen_efficientnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_efficientnet)
print("Accuracy con EfficientNetB0 entrenando las ultimas 5 capas: {}".format(accuracy))


matriz_confusion(y_test, predicciones_efficientnet)

# fine tuning de EfficientNet
red_efficientnet_b0.trainable = True
red_efficientnet_b0 = ejecutaModelo(red_efficientnet_b0, x_train, y_train, -1, 64, 20, preprocesado_efficientnet)

test_datagen_efficientnet = ImageDataGenerator(preprocessing_function = preprocesado_efficientnet)
predicciones_efficientnet = red_efficientnet_b0.predict_generator(test_datagen_efficientnet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_efficientnet)
print("Accuracy con EfficientNetB0 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_efficientnet)

#  celda para el codigo de DenseNet121, por defecto  sin include_top para añadir la capa Dense con nuestro numero de clases y pesos de imagenet
red_densenet = DenseNet121(include_top = False, pooling = "avg")
red_densenet.trainable = False
# ponemos los ultimos cinco como entrenables, el resto los fijamos
for layer in red_densenet.layers[-5:]:
  layer.trainable = True

red_densenet = ejecutaModelo(red_densenet, x_train, y_train, 1, 64, 20, preprocesado_densenet)
test_datagen_densenet = ImageDataGenerator(preprocessing_function = preprocesado_densenet)
predicciones_densenet = red_densenet.predict_generator(test_datagen_densenet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_densenet)
print("Accuracy con DenseNet121 entrenando las ultimas 5 capas: {}".format(accuracy))


matriz_confusion(y_test, predicciones_densenet)

# fine tuning de Densenet
red_densenet.trainable = True
red_densenet = ejecutaModelo(red_densenet, x_train, y_train, -1, 64, 20, preprocesado_densenet)

test_datagen_densenet = ImageDataGenerator(preprocessing_function = preprocesado_densenet)
predicciones_densenet = red_densenet.predict_generator(test_datagen_densenet.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_densenet)
print("Accuracy con DenseNet121 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_densenet)

red_inception = InceptionV3(include_top = False, pooling = "avg")
red_inception.trainable = False
for layer in red_inception.layers[-5:]:
  layer.trainable = True
red_inception = ejecutaModelo(red_inception, x_train, y_train, 1, 64, 20, preprocesado_inception)
test_datagen_inception = ImageDataGenerator(preprocessing_function = preprocesado_inception)
predicciones_inception = red_inception.predict_generator(test_datagen_inception.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_inception)
print("Accuracy con InceptionV3 entrenando las ultimas 5 capas: {}".format(accuracy))


matriz_confusion(y_test, predicciones_inception)

red_inception.trainable = True
red_inception = ejecutaModelo(red_inception, x_train, y_train, -1, 64, 20, preprocesado_inception)

test_datagen_inception = ImageDataGenerator(preprocessing_function = preprocesado_inception)
predicciones_inception = red_inception.predict_generator(test_datagen_inception.flow(x_test,
                                                            batch_size = 1,
                                                            shuffle = False),
                                                            steps = len(x_test))

accuracy = calcularAccuracy(y_test,predicciones_inception)
print("Accuracy con InceptionV3 tras ajuste fino: {}".format(accuracy))

matriz_confusion(y_test, predicciones_inception)
