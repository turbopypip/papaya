import React from 'react';
import {Box, Container, Flex, Link} from '@chakra-ui/react';
import {FaLink} from 'react-icons/fa';

const Footer = () => {
  return (
    <Container
      borderTop="1px solid gray"
      height="60px"
      fontFamily="Faculty Glyphic">
      <Flex justifyContent="space-between" alignItems="center" height="100%">
        <p>Copyright (c) VKID 2024</p>
        <Box>
          <Link href="https://github.com/Project-practice-MEPHI-2024">
            <FaLink />
            GitHub
          </Link>
        </Box>
      </Flex>
    </Container>
  );
};

export default Footer;
