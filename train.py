"""Main pytorch-vqvae training script"""

from __future__ import print_function
import os
import sys
import argparse
import torch
import torch.utils.data
from torch import nn, optim
from torch.autograd import Variable
from torchvision import datasets, transforms
from torchvision.utils import save_image
from model import VQVAE


parser = argparse.ArgumentParser(description='VQVAE MNIST Example')
parser.add_argument('--batch-size', type=int, default=128, metavar='N',
                    help='input batch size for training (default: 128)')
parser.add_argument('--epochs', type=int, default=10, metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='enables CUDA training')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                    help='how many batches to wait before logging training status')
parser.add_argument('--input-dim', default=784, type=int)
parser.add_argument('--emb-dim', default=500, type=int)
parser.add_argument('--emb-num', default=10, type=int)
parser.add_argument('--beta', default=0.3, type=float)

args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()


torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)


kwargs = {'num_workers': 1, 'pin_memory': True} if args.cuda else {}
train_loader = torch.utils.data.DataLoader(
    datasets.MNIST('../data', train=True, download=True,
                   transform=transforms.ToTensor()),
    batch_size=args.batch_size, shuffle=True, **kwargs)
test_loader = torch.utils.data.DataLoader(
    datasets.MNIST('../data', train=False, transform=transforms.ToTensor()),
    batch_size=args.batch_size, shuffle=True, **kwargs)


model = VQVAE(args.input_dim, args.emb_dim, args.emb_num, args.batch_size)
if args.cuda:
    model.cuda()


optimizer = optim.Adam(model.parameters(), lr=1e-3)


def train(epoch):
    """run one epoch of model to train with data loader"""
    model.train()
    train_loss = 0
    for batch_idx, (data, _) in enumerate(train_loader):
        data = Variable(data).view(-1, 784)
        if args.cuda:
            data = data.cuda()
        # run forward
        # compute losses
        recon_batch, reconst_loss, embed_loss, commit_loss = model(data)

        # clear gradients and run backward
        optimizer.zero_grad()
        # get gradients for decoder and encoder
        #loss = reconst_loss
        #loss = embed_loss
        #loss = commit_loss
        loss = reconst_loss + embed_loss + args.beta * commit_loss
        #loss = reconst_loss + args.beta * commit_loss
        #loss = reconst_loss# + embed_loss + args.beta * commit_loss
        #loss = reconst_loss + embed_loss# + args.beta * commit_loss 
        
        # backward for decoder and embedding
        #loss.backward()
        loss.backward(retain_graph=True)

        # backward for encoder
        #model.embed.zero_grad()
        #model.fc1.zero_grad()
        #model.fc2.zero_grad()
        #model.fc3.zero_grad()
        #model.fc4.zero_grad()
        #model.z_q.zero_grad()
        model.bwd()

        # clear gradients in VQ embedding 
        # get gradients for embedding
        #embed_loss.backward()
        #loss += embed_loss

        # run optimizer to update parameters
        optimizer.step()
        train_loss += loss.data[0]

        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader),
                loss.data[0] / len(data)))

    print('====> Epoch: {} Average loss: {:.4f}'.format(
          epoch, train_loss / len(train_loader.dataset)))


def test(epoch):
    model.eval()
    test_loss = 0
    for i, (data, _) in enumerate(test_loader):
        if args.cuda:
            data = data.cuda()
        data = Variable(data, volatile=True).view(-1, 784)
        recon_batch, reconst_loss, embed_loss, commit_loss = model(data)
        test_loss += (reconst_loss + embed_loss + args.beta*commit_loss).data[0]
        
        if i == 0:
          n = min(data.size(0), 8)
          comparison = torch.cat([data[:n].view(-1,1,28,28),
                                  recon_batch.view(args.batch_size, 1, 28, 28)[:n]])
          save_image(comparison.data.cpu(),
                     'results/reconstruction_' + str(epoch) + '.png', nrow=n)

    
    test_loss /= len(test_loader.dataset)
    print('====> Test set loss: {:.4f}'.format(test_loss))


os.makedirs('results', exist_ok=True)
for epoch in range(1, args.epochs + 1):
    train(epoch)
    test(epoch)

    # samples from discrete vectors
    sample = model.get_embed_weight()
    #sample = Variable(torch.randn(10, 500))
    if args.cuda:
       sample = sample.cuda()
    sample = model.decode(sample).cpu()
    save_image(sample.data.view(args.emb_num, 1, 28, 28),
               'results/sample_' + str(epoch) + '.png')

